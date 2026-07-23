from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import scrapy

from catalog_scraper.items import BookItem

RATING_VALUES = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def __init__(self, max_pages: int | str = 3, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.max_pages = max(1, int(max_pages))

    async def start(self):
        yield scrapy.Request(self.start_urls[0], meta={"page_number": 1})

    def parse(self, response: scrapy.http.Response):
        for product_url in response.css(
            "article.product_pod h3 a::attr(href)"
        ).getall():
            yield response.follow(product_url, callback=self.parse_book)

        page_number = int(response.meta.get("page_number", 1))
        next_page = response.css("li.next a::attr(href)").get()
        if next_page and page_number < self.max_pages:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta={"page_number": page_number + 1},
            )

    def parse_book(self, response: scrapy.http.Response) -> BookItem:
        table = {
            key.strip(): value.strip()
            for key, value in zip(
                response.css("table.table-striped th::text").getall(),
                response.css("table.table-striped td::text").getall(),
                strict=False,
            )
        }
        rating_classes = (
            response.css("div.product_main p.star-rating::attr(class)").get()
            or ""
        ).split()
        rating = next(
            (
                RATING_VALUES[class_name]
                for class_name in rating_classes
                if class_name in RATING_VALUES
            ),
            0,
        )
        breadcrumbs = [
            text.strip()
            for text in response.css("ul.breadcrumb li a::text").getall()
            if text.strip()
        ]
        category = breadcrumbs[-1] if breadcrumbs else "Uncategorised"
        availability = table.get(
            "Availability",
            response.css("p.instock.availability::text").get() or "",
        )
        stock_match = re.search(r"\d+", availability)

        item = BookItem()
        item["source_id"] = table.get("UPC", "")
        item["title"] = response.css("div.product_main h1::text").get() or ""
        item["category"] = category
        item["rating"] = rating
        item["price_gbp"] = (
            response.css("p.price_color::text").get()
            or table.get("Price (incl. tax)", "0")
        )
        item["price_excl_tax_gbp"] = table.get("Price (excl. tax)", "0")
        item["price_incl_tax_gbp"] = table.get("Price (incl. tax)", "0")
        item["tax_gbp"] = table.get("Tax", "0")
        item["availability"] = availability
        item["stock_count"] = stock_match.group() if stock_match else 0
        item["review_count"] = table.get("Number of reviews", 0)
        item["description"] = (
            response.css("#product_description + p::text").get() or ""
        )
        item["product_url"] = response.url
        image_path = response.css("div.item.active img::attr(src)").get() or ""
        item["image_url"] = response.urljoin(image_path)
        item["scraped_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        return item
