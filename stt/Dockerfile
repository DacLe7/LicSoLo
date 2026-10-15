FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/models PIP_NO_CACHE_DIR=1
RUN pip install "faster-whisper==1.1.1"
WORKDIR /app
COPY server.py .
EXPOSE 8080
CMD ["python", "server.py"]
