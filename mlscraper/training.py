import logging
import typing
from itertools import product

from mlscraper.samples import DictItem, Item, ListItem, Sample, ValueItem
from mlscraper.scrapers import DictScraper, ListScraper, ValueScraper
from mlscraper.selectors import generate_selector_for_nodes, make_matcher_for_samples
from mlscraper.util import Node


class TrainingException(Exception):
    pass


class NoScraperFoundException(TrainingException):
    pass


def train_scraper(item: Item, roots: typing.Optional[typing.List[Node]] = None):
    """
    Train a scraper able to extract the given training data.
    """
    logging.info(f"training {item}")

    # set roots to page if not set
    if roots is None:
        roots = [s.page for s in item.samples]
        logging.info(f"roots inferred: {roots}")

    assert len(item.samples) == len(roots), f"{item.samples=} != {roots=}"

    if isinstance(item, ListItem):
        # todo add root to get_matches
        matches_per_sample = [s.get_matches() for s in item.item.samples]
        for match_combi in product(*matches_per_sample):
            print(f"{match_combi=}")
            match_roots = [m.get_root() for m in match_combi]
            print(f"{match_roots=}")
            for selector in generate_selector_for_nodes(match_roots, roots):
                # roots are the newly matched root elements
                item_scraper = train_scraper(item.item, match_roots)
                scraper = ListScraper(selector, item_scraper)
                return scraper

        raise NoScraperFoundException(f"no matcher found for {item}")

    if isinstance(item, DictItem):
        # train a scraper for each key, keep roots
        scraper_per_key = {
            k: train_scraper(i, roots) for k, i in item.item_per_key.items()
        }
        return DictScraper(scraper_per_key)

    if isinstance(item, ValueItem):
        # find a selector that uniquely matches the value given the root node
        matcher = make_matcher_for_samples(item.samples, roots)
        if matcher:
            return ValueScraper(matcher.selector, matcher.extractor)
        else:
            raise NoScraperFoundException(f"deriving matcher failed for {item}")


def get_smallest_span_match_per_sample(samples: typing.List[Sample]):
    """
    Get the best match for each sample by using the smallest span.
    :param samples:
    :return:
    """
    best_match_per_sample = [
        sorted(s.get_matches(), key=lambda m: m.get_span())[0] for s in samples
    ]
    return best_match_per_sample
