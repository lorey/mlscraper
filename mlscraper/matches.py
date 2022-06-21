"""
Matches are specific elements found on a page that match a sample.
"""
import logging
import typing
from functools import cached_property
from itertools import combinations

from mlscraper.html import get_relative_depth
from mlscraper.html import get_root_node
from mlscraper.html import HTMLAttributeMatch
from mlscraper.html import HTMLTextMatch
from mlscraper.html import Node


class Match:
    """
    Occurrence of a specific sample on a page
    """

    @property
    def root(self) -> Node:
        """
        The lowest element that contains matched elements.
        """
        raise NotImplementedError()

    def has_overlap(self, other_match: "Match"):
        assert isinstance(other_match, Match)

        # early return if different document
        if self.root.root != other_match.root.root:
            return False

        return (
            # overlap if same root node
            self.root == other_match.root
            # or if one is a parent of the other one
            or self.root.has_parent(other_match.root)
            or other_match.root.has_parent(self.root)
        )

    @cached_property
    def depth(self):
        # depth of root compared to document
        return get_relative_depth(self.root, self.root.root)


class Extractor:
    """
    Class that extracts values from a node.
    """

    def extract(self, node: Node):
        raise NotImplementedError()


class TextValueExtractor(Extractor):
    """
    Class to extract text from a node.
    """

    def extract(self, node: Node):
        return node.soup.text.strip()

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def __hash__(self):
        # todo each instance equals each other instance,
        #  so this holds,
        #  but it isn't pretty
        return 0

    def __eq__(self, other):
        return isinstance(other, TextValueExtractor)


class AttributeValueExtractor(Extractor):
    """
    Extracts a value from the attribute in an html tag.
    """

    attr = None

    def __init__(self, attr):
        self.attr = attr

    def extract(self, node: Node):
        if self.attr in node.soup.attrs:
            return node.soup[self.attr]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.attr=}>"

    def __hash__(self):
        return self.attr.__hash__()

    def __eq__(self, other):
        return isinstance(other, AttributeValueExtractor) and self.attr == other.attr


class DictMatch(Match):
    match_by_key = None

    def __init__(self, match_by_key: dict):
        self.match_by_key = match_by_key

    @cached_property
    def root(self) -> Node:
        match_roots = [m.root for m in self.match_by_key.values()]
        return get_root_node(match_roots)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.match_by_key=}>"


class ListMatch(Match):
    matches = None

    def __init__(self, matches: tuple):
        self.matches = matches

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.matches=}>"

    @cached_property
    def root(self) -> Node:
        return get_root_node([m.root for m in self.matches])


class ValueMatch(Match):
    node = None
    extractor = None

    def __init__(self, node: Node, extractor: Extractor):
        self.node = node
        self.extractor = extractor

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.node=}, {self.extractor=}>"

    @property
    def root(self) -> Node:
        return self.node


def generate_all_value_matches(
    node: Node, item: str
) -> typing.Generator[Match, None, None]:
    logging.info(f"generating all value matches ({node=}, {item=})")
    for html_match in node.find_all(item):
        matched_node = html_match.node
        if isinstance(html_match, HTMLTextMatch):
            extractor = TextValueExtractor()
        elif isinstance(html_match, HTMLAttributeMatch):
            extractor = AttributeValueExtractor(html_match.attr)
        else:
            raise RuntimeError(
                f"unknown match type ({html_match=}, {type(html_match)=})"
            )
        yield ValueMatch(matched_node, extractor)


def is_disjoint_match_combination(matches):
    """
    Check if the given matches have no overlap.
    """
    return all(not m1.has_overlap(m2) for m1, m2 in combinations(matches, 2))
