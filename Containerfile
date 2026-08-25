# ABOUTME: Container image for running the cal-scraper calendar feed generator.
# ABOUTME: Python image with requests, beautifulsoup4, lxml, icalendar dependencies.

ARG BASE_IMAGE_REF=python:3.13-slim
FROM ${BASE_IMAGE_REF}

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG BASE_IMAGE_NAME=python:3.13-slim
ARG BASE_IMAGE_DIGEST

LABEL org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.base.name="${BASE_IMAGE_NAME}" \
      org.opencontainers.image.base.digest="${BASE_IMAGE_DIGEST}"

WORKDIR /app
COPY pyproject.toml .
COPY cal_scraper/ cal_scraper/

RUN pip install --no-cache-dir .

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ICS output and translation cache stored in bind-mounted volume
VOLUME /app-data

ENTRYPOINT ["/app/entrypoint.sh"]
