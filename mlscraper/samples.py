import logging
import typing
from itertools import product

from mlscraper.html import Node
from mlscraper.html import Page
from mlscraper.matches import DictMatch
from mlscraper.matches import generate_all_matches
from mlscraper.matches import ListMatch
from mlscraper.matches import Matcher
from mlscraper.selectors import CssRuleSelector
from more_itertools import flatten


class ItemStructureException(Exception):
    pass


class Sample:
    def __init__(self, page: Page, value: typing.Union[str, list, dict]):
        self.page = page
        self.value = value

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.page=}, {self.value=}>"

    def get_matches(self):
        # todo: fix creating new sample objects, maybe by using Item class?

        if isinstance(self.value, str):
            return list(generate_all_matches(self.page, self.value))

        if isinstance(self.value, list):
            matches_by_value = [Sample(self.page, v).get_matches() for v in self.value]

            # generate list of combinations
            # todo filter combinations that use the same matches twice
            match_combis = product(*matches_by_value)

            return [ListMatch(tuple(match_combi)) for match_combi in match_combis]

        if isinstance(self.value, dict):
            matches_by_key = {
                k: Sample(self.page, self.value[k]).get_matches() for k in self.value
            }

            return [
                DictMatch(dict(zip(matches_by_key.keys(), mc)))
                for mc in product(*matches_by_key.values())
            ]

        raise RuntimeError(f"unsupported value: {self.value}")


class TrainingSet:
    """
    This class turn samples into an item structure to scrape later.
    """

    item = None

    def add_sample(self, sample: Sample):
        if not self.item:
            self.item = Item.create_from(sample.value)

        self.item.add_sample(sample)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.item=}>"


class Item:
    """
    An item represents the data structure to scrape, e.g. a specific dict with keys a, b, and c.
    """

    samples = None

    @classmethod
    def create_from(cls, item):
        if isinstance(item, str):
            return ValueItem()
        elif isinstance(item, list):
            return ListItem()
        elif isinstance(item, dict):
            return DictItem()
        else:
            raise ItemStructureException(
                f"unsupported item type ({item=}, {type(item)=}"
            )

    def __init__(self):
        self.samples = []

    def add_sample(self, sample: Sample):
        self.samples.append(sample)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.samples=}>"


class DictItem(Item):
    item_per_key = None

    def __init__(self):
        super().__init__()
        self.item_per_key = {}

    def add_sample(self, sample: Sample):
        if not isinstance(sample.value, dict):
            raise ItemStructureException(f"dict expected, {sample.value} given")

        super().add_sample(sample)

        for key, value in sample.value.items():
            if key not in self.item_per_key:
                self.item_per_key[key] = Item.create_from(value)

            value_sample = Sample(sample.page, value)
            self.item_per_key[key].add_sample(value_sample)


class ListItem(Item):
    item = None

    def __init__(self):
        super().__init__()
        self.item = None

    def add_sample(self, sample: Sample):
        if not isinstance(sample.value, list):
            raise ItemStructureException(f"list expected, {sample.value} given")

        super().add_sample(sample)

        if not self.item and len(sample.value):
            self.item = Item.create_from(sample.value[0])

        for v in sample.value:
            self.item.add_sample(Sample(sample.page, v))


class ValueItem(Item):
    def add_sample(self, sample: Sample):
        if not isinstance(sample.value, str):
            raise ItemStructureException(f"str expected, {sample.value} given")
        super().add_sample(sample)


def make_training_set(pages, items):
    assert len(pages) == len(items)

    ts = TrainingSet()
    for p, i in zip(pages, items):
        ts.add_sample(Sample(p, i))

    return ts


def make_matcher_for_samples(
    samples: typing.List[Sample], roots: typing.Optional[typing.List[Node]] = None
) -> typing.Union[Matcher, None]:
    for sample in samples:
        # todo leverage generator or cache
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
    logging.info(f"generating matchers for samples {samples=} {roots=}")
    if not roots:
        roots = [s.page for s in samples]
        logging.info("roots not set, will use samples' pages")

    assert len(samples) == len(roots)

    # make a list containing sets of nodes for each possible combination of matches
    # -> enables fast searching and set ensures order
    # todo add only matches below roots here
    matches_per_sample = [s.get_matches() for s in samples]
    match_combinations = list(map(set, product(*matches_per_sample)))
    logging.info(f"match combinations: {match_combinations}")
    node_combinations = [{m.node for m in matches} for matches in match_combinations]

    for sample in samples:
        for match in sample.get_matches():
            for css_sel in match.root.generate_path_selectors():
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
