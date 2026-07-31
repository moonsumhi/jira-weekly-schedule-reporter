FROM python:3.12-slim

WORKDIR /app

COPY mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp-server/server.py .
COPY app/secret/.env ./app/secret/.env

EXPOSE 8002

CMD ["python", "server.py"]
