FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y curl procps && \
    curl -fSL -o /tmp/openjdk.tar.gz \
        https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jre_x64_linux_hotspot_17.0.8_7.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt && \
    rm /tmp/openjdk.tar.gz && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/jdk-17.0.8+7-jre \
    PATH="/opt/jdk-17.0.8+7-jre/bin:$PATH" \
    PYTHONPATH=/opt/cassanova:$PYTHONPATH

RUN useradd -m cassanova

WORKDIR /opt/cassanova


RUN pip install uv

COPY ./requirements.txt /opt/cassanova

RUN uv pip install --no-cache-dir -r requirements.txt
RUN find /opt/cassanova/cassanova/external_tools/cassandra-5-0-4/bin -type f -exec chmod +x {} \;

COPY --chown=cassanova:cassanova . /opt/cassanova

USER cassanova
WORKDIR /opt/cassanova/cassanova

CMD ["python", "run.py"]
