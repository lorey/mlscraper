import typing
from itertools import product

from mlscraper.html import Page
from mlscraper.matches import DictMatch
from mlscraper.matches import generate_all_value_matches
from mlscraper.matches import is_disjoint_match_combination
from mlscraper.matches import ListMatch


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
            return list(generate_all_value_matches(self.page, self.value))

        if isinstance(self.value, list):
            matches_by_value = [Sample(self.page, v).get_matches() for v in self.value]

            # generate list of combinations
            # todo filter combinations that use the same matches twice
            # todo create combinations only in order
            match_combis = product(*matches_by_value)

            return [
                ListMatch(tuple(match_combi))
                for match_combi in match_combis
                if is_disjoint_match_combination(match_combi)
            ]

        if isinstance(self.value, dict):
            matches_by_key = {
                k: Sample(self.page, self.value[k]).get_matches() for k in self.value
            }

            return [
                DictMatch(dict(zip(matches_by_key.keys(), mc)))
                for mc in product(*matches_by_key.values())
                if is_disjoint_match_combination(mc)
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
