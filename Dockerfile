FROM tiangolo/uvicorn-gunicorn:python3.8-alpine3.10 as base

FROM base as build
RUN apk add --no-cache gcc g++ musl-dev
COPY requirements.txt .
RUN pip install --user -r requirements.txt


FROM base
COPY --from=build /root/.local /root/.local
COPY ./app /app/app

RUN mkdir /app/data
ENV SQLALCHEMY_DATABASE_URL="sqlite:////app/data/sqlite.db?check_same_thread=False"
ENV BACKUP_FILE="/app/data/backup.json"
ENV DOMAIN_CONFIG="{}"
ENV MAX_WORKERS="1"
