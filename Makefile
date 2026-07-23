.PHONY: install scrape dashboard test lint

install:
	python -m pip install -e ".[dev]"

scrape:
	python run_pipeline.py --max-pages 3

dashboard:
	streamlit run dashboard/app.py

test:
	pytest

lint:
	ruff check .

