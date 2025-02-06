FROM python:3.12-slim

WORKDIR /app
COPY src .
COPY requirements.txt .
RUN pip install -r requirements.txt

ENTRYPOINT ["uvicorn", "consumer.app:app", "--host", "0.0.0.0", "--port", "8080", "--lifespan", "on"]