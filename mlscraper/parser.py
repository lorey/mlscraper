# everything related to parsing html
from abc import ABC

from bs4 import BeautifulSoup


class Page(ABC):
    def select(self, css_selector):
        raise NotImplementedError()


class Node(ABC):
    pass


class SoupPage(Page):

    _soup = None

    def __init__(self, soup: BeautifulSoup):
        self._soup = soup

    def select(self, css_selector):
        return [SoupNode(res) for res in self._soup.select(css_selector)]


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
