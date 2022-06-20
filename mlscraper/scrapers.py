from mlscraper.html import Node
from mlscraper.matches import Extractor
from mlscraper.selectors import Selector


class Scraper:
    def get(self, node: Node):
        raise NotImplementedError()


class DictScraper(Scraper):
    scraper_per_key = None

    def __init__(self, scraper_per_key: dict[str, Scraper]):
        self.scraper_per_key = scraper_per_key

    def get(self, node: Node):
        return {key: scraper.get(node) for key, scraper in self.scraper_per_key.items()}

    def __repr__(self):
        return f"<DictScraper {self.scraper_per_key=}>"


class ListScraper(Scraper):
    selector = None
    scraper = None

    def __init__(self, selector: Selector, scraper: Scraper):
        self.selector = selector
        self.scraper = scraper

    def get(self, node: Node):
        return [
            self.scraper.get(item_node) for item_node in self.selector.select_all(node)
        ]

    def __repr__(self):
        return f"<ListScraper {self.selector=} {self.scraper=}>"


class ValueScraper(Scraper):
    selector = None
    extractor = None

    def __init__(self, selector: Selector, extractor: Extractor):
        self.selector = selector
        self.extractor = extractor

    def get(self, node: Node):
        return self.extractor.extract(self.selector.select_one(node))

    def __repr__(self):
        return f"<ValueScraper {self.selector=}, {self.extractor=}>"
