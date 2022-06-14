import logging
import typing

from mlscraper.html import Node
from mlscraper.html import Page
from mlscraper.html import selector_matches_nodes


class Selector:
    """
    Class to select nodes from another node.
    """

    def select_one(self, node: Node) -> Node:
        raise NotImplementedError()

    def select_all(self, node: Node) -> typing.List[Node]:
        raise NotImplementedError()


class CssRuleSelector(Selector):
    def __init__(self, css_rule):
        self.css_rule = css_rule

    def select_one(self, page: Page):
        return page.select(self.css_rule)[0]

    def select_all(self, page):
        return page.select(self.css_rule)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.css_rule=}>"


def generate_selector_for_nodes(nodes, roots):
    if roots is None:
        logging.info("roots is None, setting roots manually")
        roots = [n.root for n in nodes]

    # todo roots and nodes can be uneven here because we just want to find a way
    #  to select all the nodes from the given roots

    nodes_per_root = {}
    for root in set(roots):
        nodes_per_root[root] = [n for n, r in zip(nodes, roots) if r == root]

    selectors_seen = set()

    for node in nodes:
        for sel in node.generate_path_selectors():
            logging.info(f"selector: {sel}")
            if sel not in selectors_seen:
                logging.info(
                    f"nodes per root: {nodes_per_root}",
                )
                # check if selector returns the desired nodes per root
                if all(
                    selector_matches_nodes(root, sel, nodes)
                    for root, nodes in nodes_per_root.items()
                ):
                    logging.info(f"selector matches all nodes exactly ({sel=})")
                    yield CssRuleSelector(sel)
                else:
                    logging.info(f"selector does not match nodes exactly: {sel}")

                # add to seen
                selectors_seen.add(sel)
            else:
                logging.info(f"selector already checked: {sel}")
