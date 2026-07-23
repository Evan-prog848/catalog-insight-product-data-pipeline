import sqlite3

import pytest
from scrapy.exceptions import DropItem

from catalog_scraper.pipelines import (
    DeduplicateBookPipeline,
    NormalizeBookPipeline,
    SQLiteBookPipeline,
    parse_integer,
    parse_money,
)


def raw_book(source_id: str = "book-1") -> dict:
    return {
        "source_id": source_id,
        "title": "  Example   Book ",
        "category": " Travel ",
        "rating": "Three (3)",
        "price_gbp": "£12.99",
        "price_excl_tax_gbp": "£12.99",
        "price_incl_tax_gbp": "£12.99",
        "tax_gbp": "£0.00",
        "availability": " In stock (7 available) ",
        "stock_count": "7 available",
        "review_count": "4",
        "description": "  A useful   test book. ",
        "product_url": f"https://example.test/{source_id}",
        "image_url": f"https://example.test/{source_id}.jpg",
        "scraped_at": "2026-07-23T00:00:00+00:00",
    }


def test_value_parsers():
    assert parse_money("£1,234.50") == 1234.5
    assert parse_integer("In stock (22 available)") == 22


def test_normalize_pipeline_cleans_and_converts_values():
    item = NormalizeBookPipeline().process_item(raw_book())

    assert item["title"] == "Example Book"
    assert item["price_gbp"] == 12.99
    assert item["rating"] == 3
    assert item["description"] == "A useful test book."


def test_normalize_pipeline_rejects_missing_identity():
    item = raw_book(source_id="")
    with pytest.raises(DropItem):
        NormalizeBookPipeline().process_item(item)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rating", 0),
        ("rating", 6),
        ("price_gbp", "-£1.00"),
        ("stock_count", "-1"),
        ("product_url", "not-a-url"),
    ],
)
def test_normalize_pipeline_rejects_invalid_delivery_values(field, value):
    item = raw_book()
    item[field] = value
    with pytest.raises(DropItem):
        NormalizeBookPipeline().process_item(item)


def test_duplicate_pipeline_rejects_second_occurrence():
    pipeline = DeduplicateBookPipeline()
    pipeline.open_spider()
    pipeline.process_item(raw_book())

    with pytest.raises(DropItem):
        pipeline.process_item(raw_book())


def test_sqlite_pipeline_upserts_records(tmp_path):
    database = tmp_path / "books.sqlite"
    pipeline = SQLiteBookPipeline(str(database))
    pipeline.open_spider()
    first = NormalizeBookPipeline().process_item(raw_book())
    pipeline.process_item(first)
    changed = raw_book()
    changed["title"] = "Updated Book"
    pipeline.process_item(NormalizeBookPipeline().process_item(changed))
    pipeline.close_spider()

    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT source_id, title FROM books"
        ).fetchall()
    finally:
        connection.close()
    assert rows == [("book-1", "Updated Book")]
