FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p staticf log_files \
    && touch log_files/cmd_audits.log log_files/creds_audits.log log_files/http_audit.log \
    && ssh-keygen -t rsa -b 2048 -f staticf/server.key -N ""

EXPOSE 2222 5000 8050
