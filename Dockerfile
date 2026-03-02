FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all scripts and the runner
COPY . .

EXPOSE 8141

# Added --timeout 1000 to allow long-running mover scripts
# Added --workers 2 to ensure the UI stays responsive while a script runs
CMD ["gunicorn", "--bind", "0.0.0.0:8141", "--workers", "2", "--timeout", "1000", "runner:app"]
