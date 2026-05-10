FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget fontconfig libfontconfig1 libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic binary for Linux x86_64
RUN wget -qO /tmp/tectonic.tar.gz \
    https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.16.0/tectonic-0.16.0-x86_64-unknown-linux-musl.tar.gz \
    && tar xz -C /usr/local/bin/ -f /tmp/tectonic.tar.gz \
    && rm /tmp/tectonic.tar.gz \
    && chmod +x /usr/local/bin/tectonic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output logs

CMD ["python3", "-m", "src.main"]
