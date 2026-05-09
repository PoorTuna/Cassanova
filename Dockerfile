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
    uv pip install --no-cache-dir . && \
    chgrp -R 0 /opt/venv && \
    chmod -R g=u /opt/venv

FROM python:3.12-slim AS jdk-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl binutils && \
    curl -fSL -o /tmp/openjdk.tar.gz \
        https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.8_7.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt && \
    rm /tmp/openjdk.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN /opt/jdk-17.0.8+7/bin/jlink \
    --add-modules java.base,java.compiler,java.logging,java.management,java.management.rmi,java.naming,java.net.http,java.rmi,java.security.jgss,java.security.sasl,java.sql,java.xml,jdk.attach,jdk.crypto.cryptoki,jdk.crypto.ec,jdk.jfr,jdk.management,jdk.management.jfr,jdk.unsupported,jdk.xml.dom \
    --strip-debug \
    --no-man-pages \
    --no-header-files \
    --compress=2 \
    --output /opt/jre-custom && \
    chgrp -R 0 /opt/jre-custom && \
    chmod -R g=u /opt/jre-custom

FROM python:3.12-slim AS tools-builder

COPY --from=jdk-builder /opt/jre-custom /opt/jre-custom

COPY cassanova/external_tools /opt/external_tools

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    find /opt/external_tools -type f -exec sed -i 's/\r$//' {} \; && \
    curl -fSL -o /tmp/cassandra.tar.gz \
        https://archive.apache.org/dist/cassandra/5.0.4/apache-cassandra-5.0.4-bin.tar.gz && \
    tar -xzf /tmp/cassandra.tar.gz -C /tmp && \
    cp -r /tmp/apache-cassandra-5.0.4/lib /opt/external_tools/cassandra-5-0-4/ && \
    cp -r /tmp/apache-cassandra-5.0.4/tools /opt/external_tools/cassandra-5-0-4/ && \
    rm -rf /tmp/cassandra.tar.gz /tmp/apache-cassandra-5.0.4 && \
    find /opt/external_tools/cassandra-5-0-4/bin -type f -exec chmod 0755 {} \; && \
    chgrp -R 0 /opt/external_tools && \
    chmod -R g=u /opt/external_tools

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/opt/jre-custom/bin:$PATH" \
    PYTHONPATH=/opt/cassanova:$PYTHONPATH \
    CASSANOVA_CONFIG_PATH=/opt/cassanova/cassanova.json \
    JAVA_HOME=/opt/jre-custom \
    HOME=/tmp

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    procps \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m cassanova

COPY --from=builder /opt/venv /opt/venv
COPY --from=jdk-builder /opt/jre-custom /opt/jre-custom

COPY --chown=cassanova:root . /opt/cassanova
COPY --chown=cassanova:root --from=tools-builder /opt/external_tools /opt/cassanova/cassanova/external_tools

USER cassanova
WORKDIR /opt/cassanova/cassanova

CMD ["python", "run.py"]
