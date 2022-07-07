"""
Encapsulation of html-related functionality.
BeautifulSoup should only get used here.
"""
import html
import re
import typing
from abc import ABC
from dataclasses import dataclass
from functools import cached_property

from bs4 import BeautifulSoup
from bs4.element import NavigableString
from bs4.element import Tag


# dots and slashes break bs4/soupsieve
CLASS_CHAR_BLACKLIST = tuple(":/")


class MlscraperTag(Tag):
    """
    mlscraper's own BeautifulSoup Tag that caches hashes.
    """

    def __hash__(self):
        # Why change __hash__?

        # bs4 implements Tag.__hash__ by calling str(self).__hash__()
        # which hashes the text contents of tags.
        # For our use case, this slows down many html-related functions
        # because set operations and equality checks rely on __hash__.
        # To circumvent this, we lazily cache hashes

        # warning: this assumes the soup to be static (which works for us)

        if not self._hash:
            # hash once and store
            self._hash = str(self).__hash__()

        # return stored hash
        return self._hash


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
    def page(self):
        return self._page

    @cached_property
    def depth(self):
        return self.parent.depth

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

            for p in node.ancestors:
                if p.text.strip() == node.text.strip() and not isinstance(p, Page):
                    yield HTMLExactTextMatch(p)

        # attributes
        for soup_node in self.soup.find_all():
            for attr in soup_node.attrs:
                if soup_node[attr] == item:
                    node = self._page._get_node_for_soup(soup_node)
                    yield HTMLAttributeMatch(node, attr)

        # todo implement other find methods

    def has_ancestor(self, node: "Node") -> bool:
        # early return if different page
        if self._page != node._page:
            return False

        # inline to avoid creating ancestors
        for a in self.soup.parents:
            if a == node.soup:
                return True
        return False

    @cached_property
    def parent(self):
        """
        Get parent node.
        """
        # don't return parent if it would be above <html> tag
        if self.tag_name in ["html", "[document]"]:
            return self._page

        return self._page._get_node_for_soup(self.soup.parent)

    @cached_property
    def ancestors(self) -> list["Node"]:
        """
        Return all ancestors starting with the parent.
        """
        if self.parent:
            return [self.parent] + self.parent.ancestors
        else:
            return []

    @cached_property
    def classes(self) -> tuple[str]:
        return tuple(filter(is_supported_class, self.soup.attrs.get("class", ())))

    @property
    def id(self):
        return self.soup.attrs.get("id", None)

    @property
    def tag_name(self):
        return self.soup.name

    @property
    def html_attributes(self):
        return self.soup.attrs

    def select(self, css_selector, limit=None):
        return [
            self._page._get_node_for_soup(n)
            for n in self.soup.select(css_selector, limit=limit)
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

        # use own Tag for lazy hashing
        soup = BeautifulSoup(self.html, "lxml", element_classes={Tag: MlscraperTag})

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

    @property
    def parent(self):
        return None


def get_root_node(nodes: list[Node]) -> Node:
    pages = [n._page for n in nodes]
    assert len(set(pages)) == 1, "different pages found, cannot get a root"

    # generate parent paths from top to bottom
    # [elem, parent, ancestor, root]
    parent_paths = [reversed([n] + n.ancestors) for n in nodes]

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
    hierarchy = list(reversed([node] + node.ancestors))
    assert node in hierarchy
    assert root in hierarchy
    return hierarchy.index(node) - hierarchy.index(root)


def make_selector_for_classes(class_combination: typing.Collection[str]):
    # sort to make deterministic
    # (avoid duplicates like .a.b and .b.a from different calls)
    css_selectors_classes = sorted(f".{cl}" for cl in class_combination)
    return "".join(css_selectors_classes)


def is_supported_class(cl):
    return all(c not in cl for c in CLASS_CHAR_BLACKLIST)


def get_similarity(node1: Node, node2: Node) -> float:
    if node1.tag_name != node2.tag_name:
        return 0

    jaccard_top = len(set(node1.classes).intersection(node2.classes))
    jaccard_bottom = len(set(node1.classes).union(node2.classes))
    if jaccard_top == jaccard_bottom:
        return 1  # also 0/0
    jaccard = jaccard_top / jaccard_bottom
    if node1.parent and node2.parent:
        jaccard = 0.75 * jaccard + 0.25 * get_similarity(node1.parent, node2.parent)
    return jaccard
