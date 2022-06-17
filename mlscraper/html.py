"""
Encapsulation of html-related functionality.
BeautifulSoup should only get used here.
"""
import logging
import typing
from abc import ABC
from dataclasses import dataclass
from itertools import combinations
from itertools import product

from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag
from mlscraper.util import powerset_max_length


@dataclass
class Match(ABC):
    node: "Node" = None


@dataclass
class TextMatch(Match):
    pass


@dataclass
class AttributeMatch(Match):
    attr: str = None


def _generate_css_selectors_for_node(soup: Tag, complexity: int):
    """
    Generate a selector for the given node.
    :param soup:
    :return:
    """
    assert isinstance(soup, Tag)

    # use id
    tag_id = soup.attrs.get("id", None)
    if tag_id:
        yield "#" + tag_id

    # use classes
    css_classes = soup.attrs.get("class", [])
    for css_class_combo in powerset_max_length(css_classes, complexity):
        css_clases_str = "".join([f".{css_class}" for css_class in css_class_combo])
        css_selector = soup.name + css_clases_str
        yield css_selector

    # todo: nth applies to whole selectors
    #  -> should thus be a step after actual selector generation
    if isinstance(soup.parent, Tag) and hasattr(soup, "name"):
        children_tags = [c for c in soup.parent.children if isinstance(c, Tag)]
        child_index = list(children_tags).index(soup) + 1
        yield ":nth-child(%d)" % child_index

        children_of_same_type = [c for c in children_tags if c.name == soup.name]
        child_index = children_of_same_type.index(soup) + 1
        yield ":nth-of-type(%d)" % child_index


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

    def find_all(self, item) -> typing.List[Match]:
        return list(self._generate_find_all(item))

    def _generate_find_all(self, item):
        assert isinstance(item, str), "can only search for str at the moment"

        # text
        for soup_node in self.soup.find_all(text=item):
            # use parent node as found text is NaviableString and not Tag
            node = self._page._get_node_for_soup(soup_node.parent)
            yield TextMatch(node)

        # attributes
        for soup_node in self.soup.find_all():
            for attr in soup_node.attrs:
                if soup_node[attr] == item:
                    node = self._page._get_node_for_soup(soup_node)
                    yield AttributeMatch(node, attr)

        # todo implement other find methods

    def has_parent(self, node: "Node"):
        for p in self.soup.parents:
            if p == node.soup:
                return True
        return False

    def generate_path_selectors(self, complexity: int):
        """
        Generate a selector for the path to the given node.
        :return:
        """
        if not isinstance(self.soup, Tag):
            error_msg = "Only tags can be selected with CSS, %s given" % type(self.soup)
            raise RuntimeError(error_msg)

        # we have a list of n ancestor notes and n-1 nodes including the last node
        # the last node must get selected always

        # so we will:
        # 1) generate all selectors for current node
        # 2) append possible selectors for the n-1 descendants
        # starting with all node selectors and increasing number of used descendants

        # remove unique parents as they don't improve selection
        # body is unique, html is unique, document is bs4 root element
        parents = [
            n for n in self.soup.parents if n.name not in ("body", "html", "[document]")
        ]
        # print(parents)

        # loop from i=0 to i=len(parents) as we consider all parents
        parent_node_count_max = min(len(parents), complexity)
        for parent_node_count in range(parent_node_count_max + 1):
            logging.info(
                "generating path selectors with %d parents" % parent_node_count
            )
            # generate paths with exactly parent_node_count nodes
            for parent_nodes_sampled in combinations(parents, parent_node_count):
                path_sampled = (self.soup,) + parent_nodes_sampled
                # logging.info(path_sampled)

                # make a list of selector generators for each node in the path
                # todo limit generated selectors -> huge product
                selector_generators_for_each_path_node = [
                    _generate_css_selectors_for_node(n, complexity)
                    for n in path_sampled
                ]

                # generator that outputs selector paths
                # e.g. (div, .wrapper, .main)
                path_sampled_selectors = product(
                    *selector_generators_for_each_path_node
                )

                # create an actual css selector for each selector path
                # e.g. .main > .wrapper > .div
                for path_sampled_selector in path_sampled_selectors:
                    # if paths are not directly connected, i.e. (1)-(2)-3-(4)
                    #  join must be " " and not " > "
                    css_selector = " ".join(reversed(path_sampled_selector))
                    yield css_selector

    def select(self, css_selector):
        return [
            self._page._get_node_for_soup(n) for n in self.soup.select(css_selector)
        ]

    def __repr__(self):
        if isinstance(self.soup, NavigableString):
            return f"<{self.__class__.__name__} {self.soup[:100]=}>"
        return f"<{self.__class__.__name__} {self.soup.name=} classes={self.soup.get('class', None)}, text={self.soup.text[:10]}...>"

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


def get_root_node(nodes: typing.List[Node]) -> Node:
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


def selector_matches_nodes(root: Node, selector: str, expected: typing.List[Node]):
    """
    Check whether the given selector matches the expected nodes.
    """
    # we care for equality here as selector should match the expected nodes in the exact given order
    # we do this here, as wrapping Nodes can have side effects regarding equality
    return root.soup.select(selector) == [n.soup for n in expected]
