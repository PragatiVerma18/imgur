import uuid
import logging
import pandas as pd
import io
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ProcessingJob, Image
from processing.tasks import process_images
from rest_framework import serializers

logger = logging.getLogger(__name__)


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        logger.debug("Starting file validation")
        try:
            value.seek(0)  # Ensure file is read from the beginning
            decoded_file = value.read().decode("utf-8")
            logger.debug("Decoded file content: %s", decoded_file)
            df = pd.read_csv(io.StringIO(decoded_file))
            logger.debug("CSV DataFrame: %s", df.head())
        except pd.errors.EmptyDataError:
            logger.error("CSV file is empty")
            raise serializers.ValidationError("CSV file is empty")
        except Exception as e:
            logger.error("Error reading CSV file: %s", e)
            raise serializers.ValidationError(
                "CSV file is empty or improperly formatted"
            )

        expected_columns = ["S. No.", "Product Name", "Input Image Urls"]
        if list(df.columns) != expected_columns:
            logger.error("Invalid CSV headers: %s", df.columns)
            raise serializers.ValidationError(
                "CSV file must have the following columns: 'S. No.', 'Product Name', 'Input Image Urls'"
            )

        for index, row in df.iterrows():
            logger.debug("Validating row: %s", row)
            if len(row) != 3:
                logger.error("Invalid row length: %s", row)
                raise serializers.ValidationError(
                    "Each row must have exactly 3 columns"
                )

        logger.debug("File validation completed successfully")
        return value


class UploadCSV(APIView):
    def post(self, request):
        logger.info("Received file upload request")
        if "file" not in request.FILES:
            logger.error("No file found in request")
            return Response(
                {"error": "No file found in request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        logger.info("Received file: %s", file.name)

        serializer = CSVUploadSerializer(data=request.FILES)
        if not serializer.is_valid():
            logger.error("File validation failed: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create job entry
        job = ProcessingJob.objects.create()
        logger.info("Created ProcessingJob entry with job ID: %s", job.id)

        # Read CSV and store image URLs
        try:
            file.seek(0)  # Reset file pointer before reading
            decoded_file = file.read().decode("utf-8")
            if not decoded_file.strip():
                raise pd.errors.EmptyDataError("CSV file is empty")

            logger.debug("Decoded file content: %s", decoded_file)
            df = pd.read_csv(io.StringIO(decoded_file))
            logger.debug("CSV DataFrame: %s", df.head())
        except pd.errors.EmptyDataError:
            logger.error("CSV file is empty")
            return Response(
                {"error": "CSV file is empty"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error("Error reading CSV file: %s", e)
            return Response(
                {"error": "CSV file is empty or improperly formatted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        images = []
        for index, row in df.iterrows():
            product_name = row["Product Name"]
            input_urls = row["Input Image Urls"].split(",")
            logger.debug("Product name: %s, Input URLs: %s", product_name, input_urls)

            for url in input_urls:
                images.append(
                    Image(job=job, input_url=url.strip(), product_name=product_name)
                )
                logger.debug(
                    "Added image URL: %s for product: %s", url.strip(), product_name
                )

        Image.objects.bulk_create(images)  # Optimized bulk insert
        logger.info("Bulk inserted %d images", len(images))

        # Trigger Celery task
        process_images.delay(job.id)
        logger.info("Triggered Celery task for job ID: %s", job.id)

        return Response({"request_id": job.id}, status=status.HTTP_201_CREATED)


class JobStatus(APIView):
    def get(self, request, job_id):
        logger.info("Received job status request for job ID: %s", job_id)
        try:
            job = ProcessingJob.objects.get(id=job_id)
            images = job.images.values("input_url", "output_url", "status")
            logger.info("Job status: %s", job.status)

            return Response(
                {"request_id": job_id, "status": job.status, "images": list(images)},
                status=status.HTTP_200_OK,
            )
        except ProcessingJob.DoesNotExist:
            logger.error("Job not found for job ID: %s", job_id)
            return Response(
                {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
