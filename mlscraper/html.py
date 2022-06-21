"""
Encapsulation of html-related functionality.
BeautifulSoup should only get used here.
"""
import html
import logging
import re
from abc import ABC
from dataclasses import dataclass
from functools import cached_property

from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag


@dataclass
class HTMLMatch(ABC):
    node: "Node" = None


@dataclass
class HTMLTextMatch(HTMLMatch):
    pass


@dataclass
class HTMLAttributeMatch(HTMLMatch):
    attr: str = None


class Node:
    soup = None
    _page = None

    def __init__(self, soup, page: "Page"):
        self.soup = soup
        self._page = page

    @property
    def root(self):
        return self._page

    @property
    def text(self):
        return self.soup.text

    def find_all(self, item) -> list[HTMLMatch]:
        return list(self._generate_find_all(item))

    def _generate_find_all(self, item):
        assert isinstance(item, str), "can only search for str at the moment"

        # text
        # - since text matches including whitespace, a regex is used
        for soup_node in self.soup.find_all(
            string=re.compile(r"\s*%s\s*" % html.escape(item))
        ):
            # use parent node as found text is NaviableString and not Tag
            node = self._page._get_node_for_soup(soup_node.parent)
            yield HTMLTextMatch(node)

        # attributes
        for soup_node in self.soup.find_all():
            for attr in soup_node.attrs:
                if soup_node[attr] == item:
                    node = self._page._get_node_for_soup(soup_node)
                    yield HTMLAttributeMatch(node, attr)

        # todo implement other find methods

    def has_parent(self, node: "Node"):
        for p in self.soup.parents:
            if p == node.soup:
                return True
        return False

    @cached_property
    def parents(self):
        return [self._page._get_node_for_soup(p) for p in self.soup.parents]

    @property
    def classes(self):
        return self.soup.attrs.get("class", [])

    @property
    def id(self):
        return self.soup.attrs.get("id", None)

    @property
    def tag_name(self):
        return self.soup.name

    def select(self, css_selector):
        return [
            self._page._get_node_for_soup(n) for n in self.soup.select(css_selector)
        ]

    def __repr__(self):
        if isinstance(self.soup, NavigableString):
            return f"<{self.__class__.__name__} {self.soup.strip()[:10]=}>"
        return (
            f"<{self.__class__.__name__} {self.soup.name=}"
            f" classes={self.soup.get('class', None)},"
            f" text={''.join(self.soup.stripped_strings)[:10]}...>"
        )

    def __hash__(self):
        return self.soup.__hash__()
        # return super().__hash__()

    def __eq__(self, other):
        return isinstance(other, Node) and self.soup == other.soup


class Page(Node):
    """
    One page, i.e. one HTML document.
    """

    _node_registry = None

    def __init__(self, html):
        self.html = html
        soup = BeautifulSoup(self.html, "lxml")

        # register node for each soup
        self._node_registry = {soup: self}

        super().__init__(soup, self)

    def _get_node_for_soup(self, soup) -> Node:
        if soup not in self._node_registry:
            self._node_registry[soup] = Node(soup, self)
        return self._node_registry[soup]


def get_root_node(nodes: list[Node]) -> Node:
    pages = [n._page for n in nodes]
    assert len(set(pages)) == 1, "different pages found, cannot get a root"
    root = _get_root_of_nodes(n.soup for n in nodes)
    return pages[0]._get_node_for_soup(root)


def _get_root_of_nodes(soups):
    soups = list(soups)
    assert all(isinstance(n, Tag) for n in soups)

    # root can be node itself, so it has to be added
    parent_paths_of_nodes = [[node] + list(node.parents) for node in soups]

    # paths are needed from top to bottom
    parent_paths_rev = [list(reversed(pp)) for pp in parent_paths_of_nodes]
    try:
        ancestor = _get_root_of_paths(parent_paths_rev)
    except RuntimeError as e:
        raise RuntimeError(f"No common ancestor: {soups}") from e
    return ancestor


def _get_root_of_paths(paths):
    """
    Computes the first common ancestor for list of paths.
    :param paths: list of list of nodes from top to bottom
    :return: first common index or RuntimeError
    """
    assert paths
    assert all(p for p in paths)

    # go through paths one by one, starting from bottom
    for nodes in reversed(list(zip(*paths))):
        if len(set(nodes)) == 1:
            return nodes[0]
    logging.info("failed to find ancestor for : %s", paths)
    raise RuntimeError("No common ancestor")


def get_relative_depth(node: Node, root: Node):
    node_parents = list(node.soup.parents)

    # depth of root
    i = node_parents.index(root.soup)

    # depth of element
    j = len(node_parents)

    return j - i


def selector_matches_nodes(root: Node, selector: str, expected: list[Node]):
    """
    Check whether the given selector matches the expected nodes.
    """
    logging.info(
        f"checking if selector matches nodes ({root=}, {selector=}, {expected=})"
    )
    # we care for equality here
    # as selector should match the expected nodes in the exact given order
    # we do this here, as wrapping Nodes can have side effects regarding equality
    return root.soup.select(selector) == [n.soup for n in expected]
