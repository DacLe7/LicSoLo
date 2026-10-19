FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LICHVIET_HOST=0.0.0.0
WORKDIR /app
COPY lichviet /app/lichviet
# Chạy bằng UID của người dùng máy (compose đặt "user:"), dữ liệu ở thư mục bind ./data
RUN mkdir /data && chmod 777 /data
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)"
CMD ["python", "-m", "lichviet", "/data/lichviet.db", "serve", "8080"]
