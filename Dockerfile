FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY catalog_scraper catalog_scraper
COPY dashboard dashboard
COPY exporter exporter
COPY data/sample data/sample
COPY run_pipeline.py scrapy.cfg ./
RUN python -m pip install --no-cache-dir .

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0"]
