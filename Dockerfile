FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .

ENV SESSION_DIR=/app/sessions PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
