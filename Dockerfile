FROM python:3.6-alpine

WORKDIR /app
COPY requirements.txt requirements.txt

RUN apk add --no-cache gcc musl-dev libffi-dev openssl openssl-dev \
    && pip install --no-cache -r requirements.txt \
    && apk del --no-cache gcc musl-dev libffi-dev openssl-dev

COPY k8s_secret_replicator.py k8s_secret_replicator.py

CMD ["/app/k8s_secret_replicator.py"]
