from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

REQUIRED_FIELDS = (
    "source_id",
    "title",
    "category",
    "price_gbp",
    "product_url",
    "scraped_at",
)


def load_books(database_path: str | Path) -> pd.DataFrame:
    path = Path(database_path)
    if not path.exists():
        return pd.DataFrame()
    connection = sqlite3.connect(path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM books ORDER BY category, title",
            connection,
        )
    finally:
        connection.close()


def filter_books(
    books: pd.DataFrame,
    *,
    search: str = "",
    categories: list[str] | None = None,
    minimum_rating: int = 0,
    price_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    if books.empty:
        return books.copy()

    filtered = books.copy()
    if search.strip():
        query = search.strip().casefold()
        title_match = filtered["title"].str.casefold().str.contains(
            query, regex=False, na=False
        )
        description_match = filtered["description"].str.casefold().str.contains(
            query, regex=False, na=False
        )
        filtered = filtered[title_match | description_match]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    filtered = filtered[filtered["rating"] >= minimum_rating]

    if price_range is not None:
        minimum, maximum = price_range
        filtered = filtered[filtered["price_gbp"].between(minimum, maximum)]

    return filtered.reset_index(drop=True)


def assess_data_quality(books: pd.DataFrame) -> pd.DataFrame:
    """Return client-friendly checks for the collected product records."""
    if books.empty:
        return pd.DataFrame(columns=["Check", "Issues", "Status"])

    def blank_count(columns: tuple[str, ...]) -> int:
        total = 0
        for column in columns:
            if column not in books:
                total += len(books)
                continue
            values = books[column]
            if pd.api.types.is_string_dtype(values) or values.dtype == object:
                blank = values.fillna("").astype(str).str.strip().eq("")
                total += int((values.isna() | blank).sum())
            else:
                total += int(values.isna().sum())
        return total

    prices = pd.to_numeric(books.get("price_gbp"), errors="coerce")
    ratings = pd.to_numeric(books.get("rating"), errors="coerce")
    checks = [
        ("Required fields", blank_count(REQUIRED_FIELDS)),
        (
            "Unique product IDs",
            int(books["source_id"].duplicated().sum()),
        ),
        (
            "Unique product URLs",
            int(books["product_url"].duplicated().sum()),
        ),
        (
            "Valid prices",
            int((prices.isna() | prices.lt(0)).sum()),
        ),
        (
            "Ratings between 1 and 5",
            int((ratings.isna() | ~ratings.between(1, 5)).sum()),
        ),
    ]
    return pd.DataFrame(
        [
            {
                "Check": name,
                "Issues": issues,
                "Status": "Passed" if issues == 0 else "Review",
            }
            for name, issues in checks
        ]
    )
