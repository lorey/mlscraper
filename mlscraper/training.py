import logging
import typing
from itertools import product

from mlscraper.html import Node
from mlscraper.samples import DictItem
from mlscraper.samples import Item
from mlscraper.samples import ListItem
from mlscraper.samples import make_matcher_for_samples
from mlscraper.samples import Sample
from mlscraper.samples import ValueItem
from mlscraper.scrapers import DictScraper
from mlscraper.scrapers import ListScraper
from mlscraper.scrapers import ValueScraper
from mlscraper.selectors import generate_selector_for_nodes


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

    assert len(item.samples) == len(roots), f"{len(item.samples)=} != {len(roots)=}"

    if isinstance(item, ListItem):
        # so we have to extract a list from each root
        # to do this, we take all matches we can find
        # and try to find a common selector for one of the combinations root elements
        # if that works, we've succeeded
        # if not, we're out of luck for now
        # todo add root to get_matches to receive only matches below roots
        matches_per_sample = [s.get_matches() for s in item.item.samples]
        for match_combi in product(*matches_per_sample):
            # match_combi is one possible way to combine matches to extract the list
            logging.info(f"{match_combi=}")
            # we now take the root of every element
            match_roots = [m.root for m in match_combi]
            logging.info(f"{match_roots=}")
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
