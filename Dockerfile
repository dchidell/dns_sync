FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10

COPY requirements.txt requirements.txt

RUN pip install --no-cache -r requirements.txt

COPY ./app /app/app
