from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from catalog_scraper.spiders.books import BooksSpider
from exporter.excel import export_excel

OUTPUT_FILENAMES = (
    "books.sqlite",
    "books.jsonl",
    "books_report.xlsx",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape demo catalog data and create Excel/SQLite outputs."
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Maximum number of catalog pages to scrape.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory for generated data files.",
    )
    return parser.parse_args()


def promote_outputs(staging_directory: Path, data_directory: Path) -> None:
    """Replace the previous delivery only after every new output exists."""
    missing = [
        name for name in OUTPUT_FILENAMES if not (staging_directory / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Pipeline did not produce the expected files: {', '.join(missing)}"
        )
    for name in OUTPUT_FILENAMES:
        (staging_directory / name).replace(data_directory / name)


def run_pipeline(max_pages: int, data_directory: Path) -> Path:
    data_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".catalog-insight-",
        dir=data_directory,
    ) as staging_name:
        staging_directory = Path(staging_name)
        database_path = staging_directory / "books.sqlite"
        jsonl_path = staging_directory / "books.jsonl"
        excel_path = staging_directory / "books_report.xlsx"
        settings = get_project_settings()
        settings.set("SQLITE_DATABASE", str(database_path), priority="cmdline")
        settings.set(
            "FEEDS",
            {
                str(jsonl_path): {
                    "format": "jsonlines",
                    "encoding": "utf-8",
                    "overwrite": True,
                }
            },
            priority="cmdline",
        )

        process = CrawlerProcess(settings)
        process.crawl(BooksSpider, max_pages=max_pages)
        process.start()
        export_excel(database_path, excel_path)
        promote_outputs(staging_directory, data_directory)
    return data_directory / "books_report.xlsx"


def main() -> None:
    args = parse_args()
    output = run_pipeline(args.max_pages, args.data_dir)
    print(f"Finished. Excel report: {output.resolve()}")


if __name__ == "__main__":
    main()
