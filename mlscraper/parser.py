# everything related to parsing html
import logging
import re
from abc import ABC

from bs4 import BeautifulSoup, Tag


class Page(ABC):
    def select(self, css_selector):
        raise NotImplementedError()

    def find(self, needle):
        raise NotImplementedError()


class Node(ABC):
    pass


class SoupPage(Page):

    _soup = None

    def __init__(self, soup: BeautifulSoup):
        self._soup = soup

    def select(self, css_selector):
        try:
            return [SoupNode(res) for res in self._soup.select(css_selector)]
        except NotImplementedError:
            logging.warning("ignoring selector %s: not implemented by BS4" % css_selector)
            return []

    def find(self, needle):
        assert type(needle) == str, "can only find strings ATM"
        text_matches = self._soup.find_all(text=re.compile(needle))
        logging.debug("Matches for %s: %s", needle, text_matches)
        text_parents = (ns.parent for ns in text_matches)
        tag_matches = [p for p in text_parents if extract_soup_text(p) == needle]
        return [SoupNode(m) for m in tag_matches]


def extract_soup_text(tag: Tag):
    return tag.text


class SoupNode(Node):
    _soup_node = None

    def __init__(self, node):
        self._soup_node = node

    def __eq__(self, other):
        return self._soup_node.__eq__(other._soup_node)

    def __hash__(self):
        return self._soup_node.__hash__()


def make_soup_page(html):
    soup = BeautifulSoup(html, "lxml")
    return SoupPage(soup)


class ExtractionResult:
    """Specific result found on a page"""

    node = None
    # extraction_method = None

    def __init__(self, node: Node):
        self.node = node
