# training objects
from mlscraper.parser import Page, make_soup_page


class MultiItemPageSample:
    """Sample of an item on a page containing several items."""

    page = None
    items = None

    def __init__(self, html: bytes, items: list):
        self.page = make_soup_page(html)
        self.items = items


class SingleItemPageSample:
    """Sample of an item on a page containing one item only."""

    page = None
    item = None

    def __init__(self, html: bytes, item: dict):
        self.page = make_soup_page(html)
        self.item = item

    def find_nodes(self, attr):
        needle = self.item[attr]
        return self.page.find(needle)
