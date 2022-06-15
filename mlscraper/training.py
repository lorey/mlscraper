import logging
import typing
from itertools import product

from mlscraper.matches import DictMatch
from mlscraper.matches import ListMatch
from mlscraper.matches import ValueMatch
from mlscraper.samples import TrainingSet
from mlscraper.scrapers import DictScraper
from mlscraper.scrapers import ListScraper
from mlscraper.scrapers import ValueScraper
from mlscraper.selectors import generate_selector_for_nodes
from mlscraper.selectors import PassThroughSelector
from more_itertools import first
from more_itertools import flatten
from more_itertools import unzip


class TrainingException(Exception):
    pass


class NoScraperFoundException(TrainingException):
    pass


def train_scraper(training_set: TrainingSet):
    """
    Train a scraper able to extract the given training data.
    """
    logging.info(f"training {training_set=}")

    sample_matches = [s.get_matches() for s in training_set.item.samples]
    roots = [s.page for s in training_set.item.samples]
    for match_combination in product(*sample_matches):
        logging.info(f"trying to train scraper for matches ({match_combination=})")
        scraper = train_scraper_for_matches(match_combination, roots)
        return scraper


def train_scraper_for_matches(matches, roots):
    """
    Train a scraper that finds the given matches from the given roots.
    :param matches: the matches to scrape
    :param roots: the root elements containing the matches, e.g. pages or elements on pages
    """
    found_types = set(map(type, matches))
    assert (
        len(found_types) == 1
    ), f"different match types passed {found_types=}, {matches=}"
    found_type = first(found_types)

    # make sure we have lists
    matches = list(matches)
    roots = list(roots)

    assert len(matches) == len(roots), f"got uneven inputs ({matches=}, {roots=})"
    if found_type == ValueMatch:
        logging.info("training ValueScraper")
        matches: typing.List[ValueMatch]

        # if matches have different extractors, we can't find a common scraper
        extractors = set(map(lambda m: m.extractor, matches))
        if len(extractors) != 1:
            raise NoScraperFoundException(
                "different extractors found for matches, aborting"
            )
        extractor = first(extractors)

        # early return: nodes are matched already, e.g. for List of Values
        if all(m.node == r for m, r in zip(matches, roots)):
            # nodes are matched already, done
            return ValueScraper(PassThroughSelector(), extractor=extractor)

        selector = first(
            generate_selector_for_nodes([m.node for m in matches], roots), None
        )
        if not selector:
            raise NoScraperFoundException(f"no selector found {matches=}")
        return ValueScraper(selector, extractor)
    elif found_type == DictMatch:
        logging.info("training DictScraper")
        matches: typing.List[DictMatch]

        # what if some matches have missing keys? idk
        # by using union of all keys, we'll get errors two lines below to be sure
        keys = set(flatten(m.match_by_key.keys() for m in matches))

        # train scraper for each key of dict
        # matches are the matches for the keys
        # roots are the original roots(?)
        scraper_per_key = {
            k: train_scraper_for_matches([m.match_by_key[k] for m in matches], roots)
            for k in keys
        }
        return DictScraper(scraper_per_key)
    elif found_type == ListMatch:
        logging.info("training ListScraper")
        matches: typing.List[ListMatch]

        # so we have a list of ListMatch objects
        # we have to find a selector that uniquely matches the list elements
        # todo can be one of the parents
        match_roots = [m.root for m in matches]
        logging.info(f"{match_roots=}")
        selector = first(generate_selector_for_nodes(match_roots, roots))
        if selector:
            # for all the item_matches, create a tuple
            # that contains the item_match and the new root
            matches_and_roots = [
                (im, selector.select_one(r))
                for m, r in zip(matches, roots)
                for im in m.matches
            ]
            item_matches, list_roots = unzip(matches_and_roots)
            item_scraper = train_scraper_for_matches(
                list(item_matches), list(list_roots)
            )
            return ListScraper(selector, item_scraper)
    else:
        raise RuntimeError(f"type not matched: {found_type}")
