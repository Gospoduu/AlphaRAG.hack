FROM python:3.13-slim

LABEL authors="gospoduu"

WORKDIR /app

COPY Back/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "Back/main/main.py"]
