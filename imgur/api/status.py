import logging

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from imgur.jobs.models import ProcessingJob, Image

logger = logging.getLogger(__name__)


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["id", "input_url", "output_url", "status", "product_name"]


class JobStatusSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProcessingJob
        fields = ["id", "status", "images"]


class JobStatusView(APIView):
    def get(self, request, job_id):
        logger.info("Received job status request for job ID: %s", job_id)
        try:
            job = ProcessingJob.objects.get(id=job_id)
            serializer = JobStatusSerializer(job)
            logger.info("Job status: %s", job.status)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ProcessingJob.DoesNotExist:
            logger.error("Job not found for job ID: %s", job_id)
            return Response(
                {"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND
            )
