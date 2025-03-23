FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the shroomie package and the web app
COPY app /app/
COPY entrypoint.sh /app/

# Make the entrypoint executable and fix line endings
RUN chmod +x /app/entrypoint.sh && \
    sed -i 's/\r$//' /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose the port
EXPOSE 5000

# Set the entrypoint
CMD ["/bin/sh", "/app/entrypoint.sh"]