FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ARG INSTALL_WHISPERX=true
COPY requirements.txt requirements-alignment.txt ./
RUN if [ "$INSTALL_WHISPERX" = "true" ]; then pip install --no-cache-dir -r requirements-alignment.txt; else pip install --no-cache-dir -r requirements.txt; fi
COPY app ./app
RUN useradd --create-home appuser && mkdir -p /data/uploads /data/jobs /models && chown -R appuser:appuser /app /data /models
USER appuser
ENV DATA_DIR=/data MODEL_DIR=/models
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
