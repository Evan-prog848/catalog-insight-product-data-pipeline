BOT_NAME = "catalog_scraper"

SPIDER_MODULES = ["catalog_scraper.spiders"]
NEWSPIDER_MODULE = "catalog_scraper.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 20
RETRY_TIMES = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

USER_AGENT = (
    "CatalogInsightPortfolioBot/1.0 "
    "(educational project; contact: https://github.com/Evan-prog848)"
)

ITEM_PIPELINES = {
    "catalog_scraper.pipelines.NormalizeBookPipeline": 100,
    "catalog_scraper.pipelines.DeduplicateBookPipeline": 200,
    "catalog_scraper.pipelines.SQLiteBookPipeline": 300,
}

SQLITE_DATABASE = "data/books.sqlite"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"

