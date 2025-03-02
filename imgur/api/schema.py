from drf_yasg import openapi

# Define request parameters for OutputCSVView
job_id_param = openapi.Parameter(
    "job_id",
    openapi.IN_PATH,
    description="ID of the job to fetch the CSV output for",
    type=openapi.TYPE_STRING,
    required=True,
    example="019555ad-f492-fec5-b67a-516bf988519d",
)

output_csv_responses = {
    200: openapi.Response(
        description="CSV file retrieved successfully",
        examples={
            "text/csv": "S. No.,Product Name,Input Image Urls,Output Image Urls\n1,Product1,https://example.com/image1.jpg,https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg\n2,Product2,https://example.com/image2.jpg,https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg"
        },
    ),
    400: openapi.Response(
        description="Processing not yet finished",
        examples={"application/json": {"error": "Processing not yet finished"}},
    ),
    404: openapi.Response(
        description="Job not found",
        examples={"application/json": {"error": "Job not found"}},
    ),
    500: openapi.Response(
        description="Internal server error",
        examples={"application/json": {"error": "Internal server error"}},
    ),
}

# Define request body and responses for UploadCSVView
upload_csv_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "file": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
        "webhook_url": openapi.Schema(
            type=openapi.TYPE_STRING, format=openapi.FORMAT_URI
        ),
    },
    required=["file"],
)

upload_csv_responses = {
    201: openapi.Response(
        description="File uploaded successfully",
        examples={
            "application/json": {"request_id": "019555ad-f492-fec5-b67a-516bf988519d"}
        },
    ),
    400: openapi.Response(
        description="Invalid file format",
        examples={"application/json": {"error": "Invalid file format"}},
    ),
}

# Define responses for JobStatusView
job_status_example = {
    "id": "019555ad-f492-fec5-b67a-516bf988519d",
    "status": "completed",
    "images": [
        {
            "input_url": "https://example.com/image1.jpg",
            "output_url": "https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg",
            "status": "processed",
        },
        {
            "input_url": "https://example.com/image2.jpg",
            "output_url": "https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg",
            "status": "processed",
        },
    ],
}

job_status_responses = {
    200: openapi.Response(
        description="Job status retrieved successfully",
        examples={"application/json": job_status_example},
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(type=openapi.TYPE_STRING),
                "status": openapi.Schema(type=openapi.TYPE_STRING),
                "images": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "input_url": openapi.Schema(type=openapi.TYPE_STRING),
                            "output_url": openapi.Schema(type=openapi.TYPE_STRING),
                            "status": openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
            },
        ),
    ),
    404: openapi.Response(
        description="Job not found",
        examples={"application/json": {"error": "Job not found"}},
    ),
}
