# Use Render-supported Python version
FROM python:3.13.4-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:10000", "bot:app"]
