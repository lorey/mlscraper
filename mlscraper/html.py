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


@dataclass
class HTMLMatch(ABC):
    node: "Node" = None


@dataclass
class HTMLExactTextMatch(HTMLMatch):
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
        self._hash = None

    @property
    def root(self):
        return self._page

    @cached_property
    def depth(self):
        return self.parent.depth

    @cached_property
    def parent(self):
        return self._page._get_node_for_soup(self.soup.parent)

    @cached_property
    def text(self):
        return self.soup.text

    def find_all(self, item) -> list[HTMLMatch]:
        return list(self._generate_find_all(item))

    def _generate_find_all(self, item):
        assert isinstance(item, str), "can only search for str at the moment"

        # text
        # - since text matches including whitespace, a regex is used
        target_regex = re.compile(r"^\s*%s\s*$" % html.escape(item))
        for soup_node in self.soup.find_all(string=target_regex):
            # use parent node as found text is NaviableString and not Tag
            node = self._page._get_node_for_soup(soup_node.parent)
            yield HTMLExactTextMatch(node)

            for p in node.parents:
                if p.text.strip() == node.text.strip():
                    yield HTMLExactTextMatch(p)

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

    @property
    def html_attributes(self):
        return self.soup.attrs

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
        if not self._hash:
            self._hash = self.soup.__hash__()
        return self._hash
        # return self.soup.__hash__()
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

    @property
    def depth(self):
        return 0

    def _get_node_for_soup(self, soup) -> Node:
        if soup not in self._node_registry:
            self._node_registry[soup] = Node(soup, self)
        return self._node_registry[soup]


def get_root_node(nodes: list[Node]) -> Node:
    pages = [n._page for n in nodes]
    assert len(set(pages)) == 1, "different pages found, cannot get a root"

    # generate parent paths from top to bottom
    # [elem, parent, ancestor, root]
    parent_paths = [reversed([n] + n.parents) for n in nodes]

    # start looping from bottom to top
    # zip automatically uses common length
    # -> last element is the first one, where len(nodes) roots to compare exist
    for layer_nodes in reversed(list(zip(*parent_paths))):
        if len(set(layer_nodes)) == 1:
            return layer_nodes[0]
    raise RuntimeError("no root found")


def get_relative_depth(node: Node, root: Node):
    """
    Return the relative depth of node inside tree starting from root.
    """
    hierarchy = list(reversed([node] + node.parents))
    assert node in hierarchy
    assert root in hierarchy
    return hierarchy.index(node) - hierarchy.index(root)


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
