# Start with an official Python base image (e.g., 3.11-slim)
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install uv using pip first.
# Ensure pip is up-to-date first.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies using uv
# Add --system to allow installation outside a virtual environment
# Use --no-cache to prevent caching within the image layer
RUN uv pip install --system --no-cache -r requirements.txt

# Create logs directory for application logging
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy your application code into the container
COPY . .

# Set environment variables for better logging
ENV PYTHONUNBUFFERED=1

# Expose the default port for Streamlit
EXPOSE 8501

# Define the command to run when the container starts
ENTRYPOINT ["streamlit", "run", "app.py"]
