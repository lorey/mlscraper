import functools
import logging
import re
import typing

from mlscraper.html import make_selector_for_classes
from mlscraper.html import Node
from mlscraper.html import Page
from mlscraper.util import no_duplicates_generator_decorator
from more_itertools import powerset

# ids are used with #id, classes are used, too and rel is too generic
ATTRIBUTE_SELECTOR_BLACKLIST = ("id", "class", "rel")


class Selector:
    """
    Class to select nodes from another node.
    """

    def select_one(self, node: Node) -> Node:
        raise NotImplementedError()

    def select_all(self, node: Node) -> list[Node]:
        raise NotImplementedError()


class PassThroughSelector(Selector):
    def select_one(self, node: Node) -> Node:
        return node

    def select_all(self, node: Node) -> list[Node]:
        # this does not make sense as we have only one node to pass through
        raise RuntimeError("cannot apply select_all to PassThroughSelector")


class CssRuleSelector(Selector):
    def __init__(self, css_rule):
        self.css_rule = css_rule

    def select_one(self, node: Node):
        selection = node.select(self.css_rule)
        if not selection:
            raise AssertionError(
                f"css rule does not match any node ({self.css_rule=}, {node=})"
            )
        return selection[0]

    def select_all(self, node: Node):
        return node.select(self.css_rule)

    def uniquely_selects(self, root: Node, nodes: typing.Collection[Node]):
        return _uniquely_selects(self.css_rule, root, tuple(nodes))

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.css_rule=}>"


@functools.lru_cache(10000)
def _uniquely_selects(css_rule, root, nodes):
    # limit +1
    # ensures mismatch if selection result starts with nodes
    # e.g. select returns [1,2,3,...] and nodes is [1,2,3]
    # but decreases load with many results significantly
    limit = len(nodes) + 1

    # directly using soups:
    # - avoids creating nodes for all selects
    # - increases caching effort
    return root.soup.select(css_rule, limit=limit) == [n.soup for n in nodes]

    # using select
    # - creates nodes for every soup object
    # - leverages caching
    # return root.select(self.css_rule, limit=limit) == nodes


def generate_unique_selectors_for_nodes(
    nodes: list[Node], roots, complexity: int
) -> typing.Generator[Selector, None, None]:
    """
    generate a unique selector which only matches the given nodes.
    """
    if roots is None:
        logging.info("roots is None, using pages as roots")
        roots = [n.page for n in nodes]

    nodes_per_root = {r: [n for n in nodes if n.has_ancestor(r)] for r in set(roots)}
    for selector in generate_selectors_for_nodes(nodes, roots, complexity):
        logging.info(f"check if unique: {selector}")
        if all(
            selector.uniquely_selects(r, nodes_of_root)
            for r, nodes_of_root in nodes_per_root.items()
        ):
            yield selector
        else:
            # not unique
            pass


@no_duplicates_generator_decorator
def generate_selectors_for_nodes(
    nodes: list[Node], roots, complexity: int
) -> typing.Generator[CssRuleSelector, None, None]:
    """
    Generate a selector which matches the given nodes.
    """

    logging.info(
        f"trying to find selector for nodes ({nodes=}, {roots=}, {complexity=})"
    )
    assert nodes, "no nodes given"
    assert roots, "no roots given"
    assert len(nodes) == len(roots)

    list_of_selector_sets = (set(_get_path_selectors(n, complexity)) for n in nodes)
    common_selectors = set.intersection(*list_of_selector_sets)
    yield from (CssRuleSelector(cs) for cs in _sorted_css_selectors(common_selectors))


def _sorted_css_selectors(selectors: typing.Iterable[str]):
    """
    Sorts css selectors by their complexity.
    """
    return sorted(selectors, key=len)


@functools.cache
def _get_node_selectors(node: Node):
    """
    All selectors for that node (without a path).
    """
    return tuple(set(_generate_node_selectors(node)))


def _generate_node_selectors(node: Node):
    if node.tag_name in ["html", "body"] or isinstance(node, Page):
        return

    # we have to add pseudo-selectors after generating the regular ones
    selectors = set(_generate_regular_node_selectors(node))
    yield from selectors

    # generate :nth-child
    # todo this sometimes leads to non-existent selectors?!
    if node.parent:
        for css_selector in selectors:
            is_id = css_selector.startswith("#")
            if not is_id:
                # find out which index this element has if you select
                # add one to deal with 1-based indexing
                nth = node.parent.select(css_selector).index(node) + 1
                yield f"{css_selector}:nth-child({nth})"
            else:
                # is an id, distinct enough
                pass


def _generate_regular_node_selectors(node: Node):
    """
    This generates all selectors for this specific node without ancestor selectors.
    """

    # tag name
    yield node.tag_name

    # ids
    if node.id:
        yield f"#{node.id}"

    # classes
    for class_combination in powerset(node.classes):
        if class_combination:
            class_selector = make_selector_for_classes(class_combination)
            yield class_selector
            yield f"{node.tag_name}{class_selector}"
        else:
            # empty set
            pass

    # attribute
    # todo this is actually a pseudo element and can be applied to all selectors

    def is_plain_attribute_value(v):
        """filters out attributes that are complex and yield errors"""
        return re.match(r"[A-z \-]", v)

    for attribute, value in node.html_attributes.items():
        if attribute not in ATTRIBUTE_SELECTOR_BLACKLIST:
            yield f"{node.tag_name}[{attribute}]"

            if is_plain_attribute_value(value):
                yield f'{node.tag_name}[{attribute}="{value}"]'


@functools.cache
def _get_path_selectors(node: Node, max_length: int) -> tuple[str]:
    return tuple(set(_generate_path_selectors(node, max_length)))


def _generate_path_selectors(
    node: Node, max_length: int
) -> typing.Generator[str, None, None]:
    def is_unique(css_sel: str):
        return css_sel.startswith("#")

    if max_length < 1:
        return

    # return node selectors themselves
    yield from _get_node_selectors(node)

    # return combined selectors
    for node_selector in _get_node_selectors(node):
        if not is_unique(node_selector):
            for ancestor in node.ancestors:
                for ancestor_selector in _get_path_selectors(ancestor, max_length - 1):
                    yield f"{ancestor_selector} {node_selector}"
                    if ancestor == node.parent:
                        yield f"{ancestor_selector} > {node_selector}"
        else:
            # path is unique already, no need to append ancestor selectors
            pass


@functools.cache
def _estimated_selectivity(page, selector) -> float:
    """
    This returns the estimated selectivity of the selector on the given page,
    i.e. how well the selectors filters elements.
    Selectors that are unique or cannot be found, return 1.
    Regular selectors like "a" return something close to 0.
    """
    # selectivity: higher is better, 1 is unique
    search_limit = 10
    results = page.select(selector, limit=search_limit)
    return 1 - (len(results) / search_limit)
