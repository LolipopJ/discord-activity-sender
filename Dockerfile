FROM python:3.12-slim

# Install pipenv
RUN pip install pipenv

# Set working directory
WORKDIR /app

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv sync

# Copy application code
COPY . .

# Run the application
CMD ["python", "main.py"]