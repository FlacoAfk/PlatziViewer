FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    PUBLIC_HOST=localhost \
    PLATZI_VIEWER_PATH=/app \
    PLATZI_DATA_PATH=/data

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Install only runtime dependencies used by the HTTP server and Drive proxy.
RUN pip install --no-cache-dir \
    requests==2.31.0 \
    google-api-python-client==2.108.0 \
    google-auth==2.23.0 \
    google-auth-oauthlib==1.1.0 \
    google-auth-httplib2==0.1.1

COPY . /app

RUN mkdir -p /data

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)"

CMD ["python", "-u", "server.py"]
