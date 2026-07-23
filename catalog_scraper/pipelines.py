from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

BOOK_COLUMNS = (
    "source_id",
    "title",
    "category",
    "rating",
    "price_gbp",
    "price_excl_tax_gbp",
    "price_incl_tax_gbp",
    "tax_gbp",
    "availability",
    "stock_count",
    "review_count",
    "description",
    "product_url",
    "image_url",
    "scraped_at",
)


def parse_money(value: Any) -> float:
    """Convert values such as '£51.77' into a numeric amount."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, int | float):
        return round(float(value), 2)
    text = str(value).replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        raise ValueError(f"Could not parse money value: {value!r}")
    amount = float(match.group())
    prefix = text[: match.start()]
    if "-" in prefix or (
        text.strip().startswith("(") and text.strip().endswith(")")
    ):
        amount *= -1
    return round(amount, 2)


def parse_integer(value: Any) -> int:
    """Return the first integer found in a value, or zero when absent."""
    if value is None or value == "":
        return 0
    if isinstance(value, int):
        return value
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else 0


class NormalizeBookPipeline:
    money_fields = (
        "price_gbp",
        "price_excl_tax_gbp",
        "price_incl_tax_gbp",
        "tax_gbp",
    )
    integer_fields = ("rating", "stock_count", "review_count")

    def process_item(self, item: Any) -> Any:
        adapter = ItemAdapter(item)
        for field in ("source_id", "title", "category", "availability"):
            adapter[field] = " ".join(str(adapter.get(field, "")).split())

        if not all(
            adapter.get(field)
            for field in ("source_id", "title", "category", "product_url")
        ):
            raise DropItem(
                "A product must have source_id, title, category, and product_url"
            )

        for field in self.money_fields:
            adapter[field] = parse_money(adapter.get(field))
        for field in self.integer_fields:
            adapter[field] = parse_integer(adapter.get(field))

        if not 1 <= adapter["rating"] <= 5:
            raise DropItem("Rating must be between 1 and 5")
        if any(adapter[field] < 0 for field in self.money_fields):
            raise DropItem("Money values cannot be negative")
        if adapter["stock_count"] < 0 or adapter["review_count"] < 0:
            raise DropItem("Stock and review counts cannot be negative")

        product_url = urlparse(str(adapter["product_url"]))
        if product_url.scheme not in {"http", "https"} or not product_url.netloc:
            raise DropItem("product_url must be an absolute HTTP(S) URL")

        adapter["description"] = " ".join(
            str(adapter.get("description", "")).split()
        )
        return item


class DeduplicateBookPipeline:
    def open_spider(self) -> None:
        self.seen_ids: set[str] = set()

    def process_item(self, item: Any) -> Any:
        source_id = str(ItemAdapter(item).get("source_id", ""))
        if source_id in self.seen_ids:
            raise DropItem(f"Duplicate product: {source_id}")
        self.seen_ids.add(source_id)
        return item


class SQLiteBookPipeline:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    @classmethod
    def from_crawler(cls, crawler: Any) -> SQLiteBookPipeline:
        return cls(crawler.settings.get("SQLITE_DATABASE", "data/books.sqlite"))

    def open_spider(self) -> None:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                source_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                rating INTEGER NOT NULL,
                price_gbp REAL NOT NULL,
                price_excl_tax_gbp REAL NOT NULL,
                price_incl_tax_gbp REAL NOT NULL,
                tax_gbp REAL NOT NULL,
                availability TEXT NOT NULL,
                stock_count INTEGER NOT NULL,
                review_count INTEGER NOT NULL,
                description TEXT NOT NULL,
                product_url TEXT NOT NULL,
                image_url TEXT NOT NULL,
                scraped_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def process_item(self, item: Any) -> Any:
        adapter = ItemAdapter(item)
        values = [adapter.get(column, "") for column in BOOK_COLUMNS]
        placeholders = ", ".join("?" for _ in BOOK_COLUMNS)
        updates = ", ".join(
            f"{column}=excluded.{column}"
            for column in BOOK_COLUMNS
            if column != "source_id"
        )
        self.connection.execute(
            f"""
            INSERT INTO books ({", ".join(BOOK_COLUMNS)})
            VALUES ({placeholders})
            ON CONFLICT(source_id) DO UPDATE SET {updates}
            """,
            values,
        )
        self.connection.commit()
        return item

    def close_spider(self) -> None:
        self.connection.close()
