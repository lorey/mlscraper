import logging
from collections import namedtuple
from itertools import combinations, product
from statistics import mean

from bs4 import Tag
from more_itertools import powerset, flatten


def get_common_ancestor_for_paths(paths):
    # go through path one by one
    # while len(set([paths[n][i] for n in range(len(paths))])) == 1:
    ind = None
    for i, nodes in enumerate(zip(*paths)):
        # as long as all nodes are the same
        # -> go deeper
        # else break
        if len(set(nodes)) != 1:
            # return parent of mismatch
            break

        # set after as this remembers the last common index
        ind = i

    # if index is unset, even the first nodes didn't match
    if ind is None:
        raise RuntimeError("No common ancestor")

    # as all nodes are the same, we can just use the first path
    return paths[0][ind]


def get_common_ancestor_for_nodes(nodes):
    paths_of_nodes = [list(reversed(list(node.parents))) for node in nodes]
    ancestor = get_common_ancestor_for_paths(paths_of_nodes)
    return ancestor


def get_tree_path(node):
    """
    Return the path from current node to top as list
    :param node:
    :return:
    """
    return [node] + list(node.parents)


def generate_css_selectors_for_node(node: Tag, max_classes_per_node=None):
    tag_id = node.attrs.get("id", None)
    if tag_id:
        yield "#" + tag_id

    css_classes = node.attrs.get("class", [])
    css_class_combos = filter(
        lambda ccc: max_classes_per_node is None or len(ccc) <= max_classes_per_node,
        powerset(css_classes),
    )
    for css_class_combo in css_class_combos:
        css_clases_str = "".join(
            [".{}".format(css_class) for css_class in css_class_combo]
        )
        css_selector = node.name + css_clases_str
        yield css_selector

    if type(node.parent) == Tag and hasattr(node, "name"):
        children_tags = [c for c in node.parent.children if type(c) == Tag]
        child_index = list(children_tags).index(node) + 1
        yield ":nth-child(%d)" % child_index

        children_of_same_type = [c for c in children_tags if c.name == node.name]
        child_index = children_of_same_type.index(node) + 1
        yield ":nth-of-type(%d)" % child_index

    # todo yield all combination of nodes with all combinations of selectors


def get_selectors(node, parent):
    """
    Get the best selector to the node from the parent node.
    :param node:
    :param parent:
    :return:
    """

    def matches_node(selector):
        matches = parent.select(selector)
        return matches[0] == node

    return filter(matches_node, generate_css_selectors_for_node(node))


def derive_css_selector(unique_ancestors_per_item, soup):
    """
    Find a CSS selector that matches one unique ancestor per item.
    :param unique_ancestors_per_item:
    :param soup: DOM
    :return:
    """
    # start with element selectors
    # only expand element selectors that actually match

    # 3.1 generate selectors with a generator,
    # 3.2 try them on the DOM, check that each results is exactly once in each list
    #     (ensures true positives, no false positives)
    # 3.3 store the best selector
    # break if quality is 1 or above some threshold
    # for the number of parents to consider

    # selector, score
    SelectorScoring = namedtuple("SelectorScoring", ["selector", "score"])
    best = SelectorScoring(None, 0)

    # for each candidate item
    for item in flatten(unique_ancestors_per_item):

        # for each selector of the base item
        for css_selector_item in generate_css_selectors_for_node(item):
            selector_matches = soup.select(css_selector_item)
            # check if selector matches exactly once in each list
            matches_in_exactly_one_list = [
                # check that match is in exactly one list
                sum([match in list_ for list_ in unique_ancestors_per_item]) == 1
                # for all matches of the selector
                for match in selector_matches
            ]

            score = mean(matches_in_exactly_one_list)
            scoring = SelectorScoring(css_selector_item, score)
            if scoring.score > best.score:
                best = scoring
            elif best.selector != scoring.selector:
                print("Selector discarded: {} < {}".format(scoring, best))
            else:
                # found best selector, again
                pass

    return best.selector


def generate_unique_path_selectors(node):
    soup = list(node.parents)[-1]
    for css_selector in generate_path_selectors(node):
        try:
            matches = soup.select(css_selector)
            if len(matches) == 1:
                yield css_selector
        except NotImplementedError:
            pass
            # logging.exception("Selector not implemented, cannot verify, skipping")


def generate_path_selectors(node):
    """
    Generate all possible selectors for this specific node
    :return:
    """
    if not isinstance(node, Tag):
        error_msg = "Only tags can be selected with CSS, %s given" % type(node)
        raise RuntimeError(error_msg)

    # we have a list of n ancestor notes and n-1 nodes including the last node
    # the last node must get selected always

    # so we will:
    # 1) generate all selectors for current node
    # 2) append possible selectors for the n-1 descendants
    # starting with all node selectors and increasing number of used descendants

    # remove unique parents as they don't improve selection
    # body is unique, html is unique, document is bs4 root element
    parents = [n for n in node.parents if n.name not in ("body", "html", "[document]")]
    # print(parents)

    # loop from i=0 to i=len(parents) as we consider all parents
    parent_node_count_max = min(len(parents) + 1, 2)
    for parent_node_count in range(parent_node_count_max):
        logging.info("path of length %d" % parent_node_count)
        for parent_nodes_sampled in combinations(parents, parent_node_count):
            path_sampled = (node,) + parent_nodes_sampled
            # logging.info(path_sampled)

            # make a list of selector generators for each node in the path
            # todo limit generated selectors -> huge product
            selector_generators_for_each_path_node = [
                generate_css_selectors_for_node(n, max_classes_per_node=2)
                for n in path_sampled
            ]

            # generator that outputs selector paths
            # e.g. (div, .wrapper, .main)
            path_sampled_selectors = product(*selector_generators_for_each_path_node)

            # create an actual css selector for each selector path
            # e.g. .main > .wrapper > .div
            for path_sampled_selector in path_sampled_selectors:
                css_selector = " > ".join(reversed(path_sampled_selector))
                yield css_selector
