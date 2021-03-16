FROM tiangolo/uvicorn-gunicorn:python3.8-alpine3.10 as base

FROM base as build
RUN apk add --no-cache gcc g++ musl-dev
COPY requirements.txt .
RUN pip install --user -r requirements.txt


FROM base
COPY --from=build /root/.local /root/.local
COPY ./app /app/app