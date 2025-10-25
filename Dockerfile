FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./main.py
COPY static ./static

# Railway will set $PORT for us
ENV PORT=8080
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

