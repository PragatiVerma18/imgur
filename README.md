# Imgur

> This project is a stateless system that processes image data from CSV files, compresses the images asynchronously, and provides APIs for status tracking and webhook notifications.

## Features

- Upload CSV files containing image URLs.
- Asynchronous image processing and compression.
- Store processed images in Cloudinary.
- Check the status of image processing jobs.
- Download processed image data as a CSV file.
- Webhook notifications upon job completion.

## System Design

### Tech Stack

- **Backend**: Django
- **Database**: PostgreSQL
- **Storage**: Cloudinary
- **Asynchronous Processing**: Celery + Redis

> For a detailed system design, refer to the [system_design.md](./system-design.md).

## Setup and Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- [Cloudinary Account](https://cloudinary.com/documentation/python_quickstart)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/PragatiVerma18/imgur.git
   cd imgur
   ```

2. Create a virtual environment and activate it:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database:

   ```bash
   python manage.py migrate
   ```

5. Create a `.env` file from the template:

   ```bash
   cp .env.template .env
   ```

6. Update the `.env` file with your configuration.

7. Create a superuser to access Django Admin Panel:

   ```bash
   python manage.py createsuperuser
   ```

   Follow the prompts to create a superuser account.

8. Run the development server:

   ```bash
   python manage.py runserver
   ```

9. Start the Celery worker:

   ```bash
   celery -A imgur worker --loglevel=info
   ```

### Example Files

- [example.csv](./example.csv): Example input CSV file.
- [example_output.csv](./example_output.csv): Example output CSV file.
