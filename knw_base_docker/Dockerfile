FROM python:3.12-slim
RUN groupadd -r groupknw_base && \
    useradd -r -g groupknw_base userknw_base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /www/app


RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY ./ ./
USER userknw_base