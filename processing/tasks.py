from celery import shared_task
import cloudinary.uploader
from django.core.exceptions import ObjectDoesNotExist
from jobs.models import ProcessingJob, Image
import requests
from io import BytesIO
from PIL import Image as PILImage
import logging
from django.db import transaction
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def process_images(self, job_id):
    logger.info("Starting image processing for job ID: %s", job_id)
    try:
        with transaction.atomic():
            job = ProcessingJob.objects.filter(
                id=job_id,
                status="pending",
            ).first()

            if not job:
                logger.error("Job not found for job ID: %s", job_id)
                raise ObjectDoesNotExist("Job not found")

            job.status = "processing"
            job.save()
            logger.info("Job status updated to processing for job ID: %s", job_id)

        images = Image.objects.filter(job=job, status="pending")

        for img in images:
            try:
                # Download the image
                response = requests.get(img.input_url)
                if response.status_code != 200:
                    with transaction.atomic():
                        img.status = "failed"
                        img.save()
                    logger.error("Failed to download image from URL: %s", img.input_url)
                    continue

                # Open and compress the image
                image_data = BytesIO(response.content)
                pil_image = PILImage.open(image_data)
                output_buffer = BytesIO()

                # Compress image (reduce quality by 50%)
                pil_image.save(output_buffer, format=pil_image.format, quality=50)
                output_buffer.seek(0)

                # Upload to Cloudinary
                cloudinary_response = cloudinary.uploader.upload(output_buffer)
                logger.debug("Cloudinary response: %s", cloudinary_response)
                with transaction.atomic():
                    img.output_url = cloudinary_response["secure_url"]
                    img.status = "processed"
                    img.save()
                logger.info("Processed and uploaded image for URL: %s", img.input_url)
            except Exception as e:
                with transaction.atomic():
                    img.status = "failed"
                    img.save()
                logger.error(
                    "Failed to process image for URL: %s, error: %s",
                    img.input_url,
                    str(e),
                )
                try:
                    self.retry(countdown=2**self.request.retries)
                except MaxRetriesExceededError:
                    logger.error(
                        "Max retries exceeded for image URL: %s", img.input_url
                    )

        # Check if all images are processed and have an output URL
        all_images_processed = (
            Image.objects.filter(job=job, status="processed").count()
            == Image.objects.filter(job=job).count()
        )

        if all_images_processed:
            with transaction.atomic():
                # Update job status
                job.status = "completed"
                job.save()
                logger.info("Job status updated to completed for job ID: %s", job_id)

        # TODO: Trigger webhook
    except Exception as e:
        logger.error(
            "Error processing images for job ID: %s, error: %s", job_id, str(e)
        )
        return {"error": str(e)}
