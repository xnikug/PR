FROM python:3.10-slim

WORKDIR /app

COPY server.py /app/
COPY client.py /app/
COPY test_concurrent.py /app/
COPY test_rate_limit.py /app/
COPY server.conf /app/
COPY docker-entrypoint.py /app/
COPY public/ /app/public/
COPY client_saves/ /app/client_saves/
COPY src/ /app/src/

RUN chmod +x /app/docker-entrypoint.py

EXPOSE 8080

CMD ["python3", "/app/docker-entrypoint.py"]