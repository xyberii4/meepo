FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
        xvfb \
        wget \
        gnupg \
        unzip \
        fonts-liberation \
        libasound2-dev \
        libgtk-3-0 \
        libxss1 \
        libdbus-glib-1-2 \
        libnss3-dev \
        libxrandr2 \
        libgbm1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxcursor1 \
        libxi6 \
        libxtst6 \
        xvfb \
        wget \
        gnupg \
        unzip \
        fonts-liberation \
        libasound2-dev \
        libgtk-3-0 \
        libxss1 \
        libdbus-glib-1-2 \
        libnss3-dev \
        libxrandr2 \
        libgbm1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxcursor1 \
        libxi6 \
        libxtst6

RUN apt-get update && apt-get install -y chromium chromium-driver && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
WORKDIR /app
ENV PYTHONPATH=/app/src

CMD ["bash", "-c", "xvfb-run -a python -m bot.server >> /app/bot.log 2>&1"]
