# ABOUTME: Container image for running the cal-scraper calendar feed generator.
# ABOUTME: Python image with requests, beautifulsoup4, lxml, icalendar dependencies.

FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml .
COPY cal_scraper/ cal_scraper/

RUN pip install --no-cache-dir .

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Output .ics files go to a bind-mounted volume
VOLUME /data

ENTRYPOINT ["/app/entrypoint.sh"]
