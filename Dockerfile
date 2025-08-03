# Use the official Python 3.11 slim image as a base
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (so logs appear immediately)
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for certain Python packages (e.g., faiss, PyTorch CPU wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip, install all Python dependencies, then install PyTorch CPU wheels
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
    
# Copy the rest of the application code
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the app on port 8080 to match Cloud Run's requirement
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
