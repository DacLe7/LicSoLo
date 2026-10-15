FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/models PIP_NO_CACHE_DIR=1
# huggingface_hub phải < 1.0: bản mới không còn kéo theo "requests" mà faster-whisper 1.1.1 vẫn import.
RUN pip install "faster-whisper==1.1.1" "huggingface_hub<1.0" requests \
 && python -c "import faster_whisper, requests; print('stt deps ok')"
WORKDIR /app
COPY server.py .
EXPOSE 8080
CMD ["python", "server.py"]
