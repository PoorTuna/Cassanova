FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && \
    curl -fSL -o /tmp/openjdk.tar.gz https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.8+7/OpenJDK17U-jre_x64_linux_hotspot_17.0.8_7.tar.gz && \
    tar -xzf /tmp/openjdk.tar.gz -C /opt && \
    rm /tmp/openjdk.tar.gz && \
    apt-get install -y procps && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/jdk-17.0.8+7-jre \
    PATH="/opt/jdk-17.0.8+7-jre/bin:$PATH"

WORKDIR /opt/cassanova

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "cassanova.run"]
