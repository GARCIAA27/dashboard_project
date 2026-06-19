FROM python:3.12-slim

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run fastapi application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
