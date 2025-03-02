import csv
import io

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import HttpResponse

from imgur.jobs.models import ProcessingJob, Image


class OutputCSVView(APIView):
    def get(self, request, job_id):
        try:
            job = ProcessingJob.objects.filter(id=job_id).first()

            if not job:
                return Response(
                    {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
                )

            if job.status != ProcessingJob.STATUS_COMPLETED:
                return Response(
                    {"error": "Processing not yet finished"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            images = Image.objects.filter(job=job)
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["S. No.", "Product Name", "Input Image Urls", "Output Image Urls"]
            )

            grouped_images = {}
            for img in images:
                if img.product_name not in grouped_images:
                    grouped_images[img.product_name] = []
                grouped_images[img.product_name].append(img)

            index = 1
            for product_name, imgs in grouped_images.items():
                input_urls = ", ".join([img.input_url for img in imgs])
                output_urls = ", ".join([img.output_url for img in imgs])
                writer.writerow([index, product_name, input_urls, output_urls])
                index += 1

            output.seek(0)
            response = HttpResponse(output, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="output_{job_id}.csv"'
            )
            return response

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
