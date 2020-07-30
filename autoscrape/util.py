from collections import namedtuple
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


def generate_css_selectors_for_node(node: Tag):
    css_classes = node.attrs.get("class", [])
    for css_class_combo in powerset(css_classes):
        css_clases_str = "".join(
            [".{}".format(css_class) for css_class in css_class_combo]
        )
        css_selector = node.name + css_clases_str
        yield css_selector

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
