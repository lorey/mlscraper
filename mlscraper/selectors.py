import logging
import typing
from itertools import product

from more_itertools import flatten

from mlscraper.samples import Sample
from mlscraper.util import Matcher, Node, Page, Selector


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
        roots = [n.get_root() for n in nodes]

    nodes_per_root = {}
    for root in set(roots):
        nodes_per_root[root] = {n for n, r in zip(nodes, roots) if r == root}

    selectors_seen = set()

    for node in nodes:
        for sel in node.generate_path_selectors():
            if sel not in selectors_seen:
                print([set(root.select(sel)) for root in nodes_per_root.keys()])
                print([nodes_per_root[root] for root in nodes_per_root.keys()])
                if all(
                    set(root.select(sel)) == nodes_per_root[root]
                    for root in nodes_per_root.keys()
                ):
                    yield CssRuleSelector(sel)
                else:
                    logging.info(f"selector does not match nodes exactly: {sel}")

                # add to seen
                selectors_seen.add(sel)
            else:
                logging.info(f"selector already checked: {sel}")


def make_matcher_for_samples(
    samples: typing.List[Sample], roots: typing.Optional[typing.List[Node]] = None
) -> typing.Union[Matcher, None]:
    for sample in samples:
        assert sample.get_matches(), f"no matches found for {sample}"

    for matcher in generate_matchers_for_samples(samples, roots):
        return matcher
    return None


def generate_matchers_for_samples(
    samples: typing.List[Sample], roots: typing.Optional[typing.List[Node]] = None
) -> typing.Generator:
    """
    Generate CSS selectors that match the given samples.
    :param samples:
    :param roots: root nodes to search from
    :return:
    """
    logging.info(f"generating matchers for samples {samples}")
    if not roots:
        roots = [s.page for s in samples]

    assert len(samples) == len(roots)

    # make a list containing sets of nodes for each possible combination of matches
    # -> enables fast searching and set ensures order
    # todo add only matches below roots here
    matches_per_sample = [s.get_matches() for s in samples]
    match_combinations = list(map(set, product(*matches_per_sample)))
    node_combinations = [
        {m.get_root() for m in matches} for matches in match_combinations
    ]

    for sample in samples:
        for match in sample.get_matches():
            for css_sel in match.get_root().generate_path_selectors():
                logging.info(f"testing selector: {css_sel}")
                matched_nodes = set(flatten(root.select(css_sel) for root in roots))
                if matched_nodes in node_combinations:
                    logging.info(f"{css_sel} matches one of the possible combinations")
                    i = node_combinations.index(matched_nodes)
                    matches = match_combinations[i]
                    match_extractors = {m.extractor for m in matches}
                    if len(match_extractors) == 1:
                        logging.info(f"{css_sel} matches same extractors")
                        selector = CssRuleSelector(css_sel)
                        extractor = next(iter(match_extractors))
                        yield Matcher(selector, extractor)
                    else:
                        logging.info(
                            f"{css_sel} would need different extractors, ignoring: {match_extractors}"
                        )
