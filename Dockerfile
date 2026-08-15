# App image: code only, deps live in the base image.
FROM premdharshan/sourcerer-base:latest

WORKDIR /app

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
