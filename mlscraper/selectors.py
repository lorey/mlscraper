import logging
from itertools import product

from mlscraper.html import Node
from mlscraper.util import no_duplicates_generator_decorator
from more_itertools import first
from more_itertools import powerset


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
                f"css rule does not match on node ({self.css_rule=}, {node=})"
            )
        return selection[0]

    def select_all(self, node: Node):
        return node.select(self.css_rule)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.css_rule=}>"


def generate_unique_selectors_for_nodes(nodes: list[Node], roots, complexity: int):
    """
    generate a unique selector which only matches the given nodes.
    """
    if roots is None:
        logging.info("roots is None, setting roots manually")
        roots = [n.root for n in nodes]

    nodes_per_root = {r: [n for n in nodes if n.has_parent(r)] for r in set(roots)}
    for selector in generate_selectors_for_nodes(nodes, roots, complexity):
        if all(
            selector.select_all(r) == nodes_of_root
            for r, nodes_of_root in nodes_per_root.items()
        ):
            yield selector


@no_duplicates_generator_decorator
def generate_selectors_for_nodes(nodes: list[Node], roots, complexity: int):
    """
    Generate a selector which matches the given nodes.
    """

    logging.info(
        f"trying to find selector for nodes ({nodes=}, {roots=}, {complexity=})"
    )
    assert nodes, "no nodes given"
    assert roots, "no roots given"
    assert len(nodes) == len(roots)

    direct_css_selectors = list(_generate_direct_css_selectors_for_nodes(nodes))
    for direct_css_selector in direct_css_selectors:
        yield CssRuleSelector(direct_css_selector)

    parents_of_nodes_below_roots = [
        [p for p in n.parents if p.has_parent(r) and p.tag_name not in ["html", "body"]]
        for n, r in zip(nodes, roots)
    ]
    for parent_nodes in product(*parents_of_nodes_below_roots):
        for parent_selector_raw in _generate_direct_css_selectors_for_nodes(
            parent_nodes
        ):
            for css_selector_raw in direct_css_selectors:
                css_selector_combined = parent_selector_raw + " " + css_selector_raw
                yield CssRuleSelector(css_selector_combined)


def _generate_direct_css_selectors_for_nodes(nodes: list[Node]):
    logging.info(f"generating direct css selector for nodes ({nodes=})")
    common_classes = set.intersection(*[set(n.classes) for n in nodes])

    is_same_tag = len({n.tag_name for n in nodes}) == 1
    common_tag_name = nodes[0].tag_name
    yield common_tag_name

    common_ids = {n.id for n in nodes}
    is_same_id = len(common_ids) == 1
    if is_same_id and None not in common_ids:
        yield "#" + first(common_ids)

    for class_combination in powerset(common_classes):
        if class_combination:
            logging.info(f"- generating selector for ({class_combination=})")
            css_selector = "".join(map(lambda cl: "." + cl, class_combination))
            yield css_selector
            if is_same_tag:
                yield common_tag_name + css_selector
        else:
            # empty combination -> ignore
            pass
