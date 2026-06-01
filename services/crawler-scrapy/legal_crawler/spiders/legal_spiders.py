import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class PravoGovSpider(CrawlSpider):
    name = "pravo_gov"
    allowed_domains = ["pravo.gov.ru"]
    start_urls = ["http://pravo.gov.ru/"]

    rules = (
        Rule(LinkExtractor(allow=r"/document/\d+"), callback="parse_document", follow=True),
        Rule(LinkExtractor(allow=r"/block/\w+"), follow=True),
    )

    custom_settings = {"DOWNLOAD_DELAY": 3}

    def parse_document(self, response):
        title = response.css("h1::text, .document-title::text").get("").strip()
        content = "\n".join(response.css("article ::text, .document-content ::text, .text ::text").getall()).strip()
        if content:
            yield {"url": response.url, "title": title, "content": f"# {title}\n\n{content}"}


class SudactSpider(CrawlSpider):
    name = "sudact"
    allowed_domains = ["sudact.ru"]
    start_urls = ["https://sudact.ru/"]

    rules = (
        Rule(LinkExtractor(allow=r"/\w+/doc/"), callback="parse_doc", follow=True),
    )

    custom_settings = {"DOWNLOAD_DELAY": 4}

    def parse_doc(self, response):
        title = response.css("h1::text").get("").strip()
        content = "\n".join(response.css(".document-text ::text, .doc-content ::text").getall()).strip()
        if content:
            yield {"url": response.url, "title": title, "content": f"# {title}\n\n{content}"}


class CyberleninkaSpider(CrawlSpider):
    name = "cyberleninka"
    allowed_domains = ["cyberleninka.ru"]
    start_urls = ["https://cyberleninka.ru/search?q=юриспруденция"]

    rules = (
        Rule(LinkExtractor(allow=r"/article/n/"), callback="parse_article", follow=True),
    )

    def parse_article(self, response):
        title = response.css("h1::text").get("").strip()
        abstract = response.css(".abstract ::text").get("").strip()
        content = "\n".join(response.css("#article-text ::text").getall()).strip()
        full = f"# {title}\n\n## Аннотация\n{abstract}\n\n## Текст\n{content}"
        if content or abstract:
            yield {"url": response.url, "title": title, "content": full}


class PravoRuSpider(scrapy.Spider):
    name = "pravo_ru"
    allowed_domains = ["pravo.ru"]
    start_urls = ["https://pravo.ru/news/"]

    def parse(self, response):
        for link in response.css("a.news-item::attr(href), .news-list a::attr(href)").getall():
            yield response.follow(link, self.parse_article)

    def parse_article(self, response):
        title = response.css("h1::text").get("").strip()
        content = "\n".join(response.css("article ::text, .article-body ::text").getall()).strip()
        if content:
            yield {"url": response.url, "title": title, "content": f"# {title}\n\n{content}"}


class RgRuSpider(scrapy.Spider):
    name = "rg_ru"
    allowed_domains = ["rg.ru"]
    start_urls = ["https://rg.ru/pravo.html"]

    def parse(self, response):
        for link in response.css(".b-material-list__item a::attr(href), .item a::attr(href)").getall():
            yield response.follow(link, self.parse_article)

    def parse_article(self, response):
        title = response.css("h1::text").get("").strip()
        content = "\n".join(response.css(".b-material-text ::text, article ::text").getall()).strip()
        if content:
            yield {"url": response.url, "title": title, "content": f"# {title}\n\n{content}"}
