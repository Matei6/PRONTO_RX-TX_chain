FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        git \
        pkg-config \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        gnuradio \
        uhd-host \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

WORKDIR /app/ihmv2

ENV FOSM_FLASK_HOST=0.0.0.0 \
    FOSM_FLASK_PORT=5000 \
    FOSM_FLASK_DEBUG=0 \
    FOSM_ALLOW_UNSAFE_WERKZEUG=1

EXPOSE 5000

CMD ["python3", "app.py"]
