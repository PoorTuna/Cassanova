FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libsasl2-dev \
    python3-dev \
    libldap2-dev \
    libssl-dev

COPY requirements.txt .

RUN pip install uv && \
    uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/opt/jdk-17.0.8+7-jre/bin:$PATH" \
    PYTHONPATH=/opt/cassanova:$PYTHONPATH

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    procps \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev && \
    curl -fSL -o /tmp/openjdk.tar.gz \
        https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jre_x64_linux_hotspot_17.0.8_7.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt && \
    rm /tmp/openjdk.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
ENV JAVA_HOME=/opt/jdk-17.0.8+7-jre

RUN useradd -m cassanova

WORKDIR /opt/cassanova

COPY --from=builder /opt/venv /opt/venv

COPY --chown=cassanova:cassanova . /opt/cassanova

RUN find /opt/cassanova/cassanova/external_tools/cassandra-5-0-4/bin -type f -exec chmod +x {} \;

USER cassanova
WORKDIR /opt/cassanova/cassanova

CMD ["python", "run.py"]
