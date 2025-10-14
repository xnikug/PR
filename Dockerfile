FROM python:3.10-slim

WORKDIR /app

COPY server.py /app/
COPY public/ /app/public/

EXPOSE 8080

CMD ["python3", "server.py", "/app/public", "8080"]