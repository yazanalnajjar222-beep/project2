FROM python:3.14-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY frontend/ ../frontend/

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "server:app"]
