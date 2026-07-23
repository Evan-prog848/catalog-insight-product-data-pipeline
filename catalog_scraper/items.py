import scrapy


class BookItem(scrapy.Item):
    source_id = scrapy.Field()
    title = scrapy.Field()
    category = scrapy.Field()
    rating = scrapy.Field()
    price_gbp = scrapy.Field()
    price_excl_tax_gbp = scrapy.Field()
    price_incl_tax_gbp = scrapy.Field()
    tax_gbp = scrapy.Field()
    availability = scrapy.Field()
    stock_count = scrapy.Field()
    review_count = scrapy.Field()
    description = scrapy.Field()
    product_url = scrapy.Field()
    image_url = scrapy.Field()
    scraped_at = scrapy.Field()

