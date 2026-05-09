FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libsasl2-dev \
    python3-dev \
    libldap2-dev \
    libssl-dev

COPY pyproject.toml .

RUN pip install uv && \
    uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache-dir .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/opt/jdk-17.0.8+7/bin:$PATH" \
    PYTHONPATH=/opt/cassanova:$PYTHONPATH \
    CASSANOVA_CONFIG_PATH=/opt/cassanova/cassanova.json

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    procps \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev && \
    curl -fSL -o /tmp/openjdk.tar.gz \
        https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.8_7.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt && \
    rm /tmp/openjdk.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/opt/jdk-17.0.8+7

RUN useradd -m cassanova

WORKDIR /opt/cassanova

COPY --from=builder /opt/venv /opt/venv

COPY --chown=cassanova:cassanova . /opt/cassanova

# Strip Windows CRLF from committed scripts/conf before adding downloaded JARs
RUN find /opt/cassanova/cassanova/external_tools -type f -exec sed -i 's/\r$//' {} \;

# Download Cassandra JARs (not committed due to size)
RUN curl -fSL -o /tmp/cassandra.tar.gz \
        https://archive.apache.org/dist/cassandra/5.0.4/apache-cassandra-5.0.4-bin.tar.gz && \
    tar -xzf /tmp/cassandra.tar.gz -C /tmp && \
    cp -r /tmp/apache-cassandra-5.0.4/lib \
          /opt/cassanova/cassanova/external_tools/cassandra-5-0-4/ && \
    cp -r /tmp/apache-cassandra-5.0.4/tools \
          /opt/cassanova/cassanova/external_tools/cassandra-5-0-4/ && \
    rm -rf /tmp/cassandra.tar.gz /tmp/apache-cassandra-5.0.4

RUN find /opt/cassanova/cassanova/external_tools/cassandra-5-0-4/bin -type f -exec chmod 0755 {} \; && \
    chmod 0755 /opt/jdk-17.0.8+7/bin/* && \
    chgrp -R 0 /opt/cassanova /opt/venv /opt/jdk-17.0.8+7 && \
    chmod -R g=u /opt/cassanova /opt/venv /opt/jdk-17.0.8+7

ENV HOME=/tmp
USER cassanova
WORKDIR /opt/cassanova/cassanova

CMD ["python", "run.py"]
