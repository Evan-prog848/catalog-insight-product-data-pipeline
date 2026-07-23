from pathlib import Path

from scrapy.http import HtmlResponse, Request

from catalog_scraper.spiders.books import BooksSpider


def detail_response() -> HtmlResponse:
    html = Path("tests/fixtures/book_detail.html").read_text(encoding="utf-8")
    url = "https://books.toscrape.com/catalogue/a-light_1000/index.html"
    return HtmlResponse(
        url=url,
        body=html.encode(),
        encoding="utf-8",
        request=Request(url=url),
    )


def test_parse_book_extracts_core_fields():
    item = BooksSpider().parse_book(detail_response())

    assert item["source_id"] == "a897fe39b1053632"
    assert item["title"] == "A Light in the Attic"
    assert item["category"] == "Travel"
    assert item["rating"] == 3
    assert item["stock_count"] == "22"


def test_parse_book_resolves_image_and_product_urls():
    item = BooksSpider().parse_book(detail_response())

    assert item["product_url"].endswith("/a-light_1000/index.html")
    assert item["image_url"].startswith("https://books.toscrape.com/")


def test_max_pages_never_falls_below_one():
    assert BooksSpider(max_pages=0).max_pages == 1

