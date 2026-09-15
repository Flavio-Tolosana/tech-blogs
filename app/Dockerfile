FROM python:3.12-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./app

# Uso no-root por seguridad
RUN useradd --create-home --uid 1000 appuser
USER appuser

ENV OUTPUT_DIR=/data

ENTRYPOINT ["python", "-m", "app"]