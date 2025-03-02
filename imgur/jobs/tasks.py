import logging
import requests
from io import BytesIO

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
import cloudinary.uploader
from PIL import Image as PILImage

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from imgur.jobs.models import ProcessingJob, Image

logger = logging.getLogger(__name__)


def process_single_image(img):
    try:
        # Download the image
        response = requests.get(img.input_url)
        if response.status_code != 200:
            logger.error("Failed to download image from URL: %s", img.input_url)
            return False

        # Open and compress the image
        image_data = BytesIO(response.content)
        pil_image = PILImage.open(image_data)
        output_buffer = BytesIO()

        # Compress image (reduce quality by 50%)
        pil_image.save(output_buffer, format=pil_image.format, quality=50)
        output_buffer.seek(0)

        # Upload to Cloudinary
        cloudinary_response = cloudinary.uploader.upload(output_buffer)
        img.output_url = cloudinary_response["secure_url"]
        img.status = Image.STATUS_PROCESSED
        img.save(update_fields=["output_url", "status", "updated_at"])

        logger.info("Processed and uploaded image for URL: %s", img.input_url)
        return True
    except Exception as e:
        logger.error(
            "Failed to process image for URL: %s, error: %s",
            img.input_url,
            str(e),
        )
        return False


def trigger_webhook(job):
    """Send webhook notification when job is completed"""
    if not job.webhook_url:
        logger.warning("No webhook URL provided for job ID: %s", job.id)
        return

    # Prepare payload
    images = Image.objects.filter(job=job).values(
        "product_name", "input_url", "output_url", "status"
    )
    payload = {
        "job_id": str(job.id),
        "status": job.status,
        "images": list(images),
    }

    try:
        response = requests.post(job.webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info("Webhook successfully triggered for job ID: %s", job.id)
    except requests.RequestException as e:
        logger.error(
            "Failed to trigger webhook for job ID: %s, error: %s", job.id, str(e)
        )


@shared_task(bind=True, max_retries=5)
def process_images(self, job_id):
    logger.info("Starting image processing for job ID: %s", job_id)

    try:
        # Fetch job if status is PENDING or PROCESSING
        job = ProcessingJob.objects.filter(
            id=job_id,
            status__in=[ProcessingJob.STATUS_PENDING, ProcessingJob.STATUS_PROCESSING],
        ).first()

        if not job:
            logger.error("Job not found or already completed for job ID: %s", job_id)
            return {"error": "Job not found or already completed"}

        # Only update to "PROCESSING" if it's still "PENDING"
        if job.status == ProcessingJob.STATUS_PENDING:
            with transaction.atomic():
                job.status = ProcessingJob.STATUS_PROCESSING
                job.save(update_fields=["status", "updated_at"])
                logger.info("Job status updated to PROCESSING for job ID: %s", job_id)

        # Process only pending images
        images = Image.objects.filter(job=job, status=Image.STATUS_PENDING)

        for img in images:
            try:
                success = process_single_image(img)
                if not success:
                    raise Exception("Image processing failed")
            except Exception:
                try:
                    self.retry(countdown=2**self.request.retries)
                except MaxRetriesExceededError:
                    logger.error(
                        "Max retries exceeded for image URL: %s", img.input_url
                    )

        # Check if all images are processed
        total_images = Image.objects.filter(job=job).count()
        processed_images = Image.objects.filter(
            job=job, status=Image.STATUS_PROCESSED
        ).count()

        if total_images == processed_images:
            with transaction.atomic():
                job.status = ProcessingJob.STATUS_COMPLETED
                job.save(update_fields=["status", "updated_at"])
                logger.info("Job status updated to COMPLETED for job ID: %s", job_id)

            # Trigger webhook after job completion
            trigger_webhook(job)

    except Exception as e:
        logger.error(
            "Error processing images for job ID: %s, error: %s", job_id, str(e)
        )
        return {"error": str(e)}
