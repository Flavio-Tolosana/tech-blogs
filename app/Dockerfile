FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fetch_blogs.py .

# Uso no-root por seguridad
RUN useradd --create-home --uid 1000 appuser
USER appuser

ENV OUTPUT_DIR=/data

ENTRYPOINT ["python", "fetch_blogs.py"]