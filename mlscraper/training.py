import logging
from itertools import combinations
from itertools import product
from statistics import mean

from mlscraper.matches import DictMatch
from mlscraper.matches import ListMatch
from mlscraper.matches import ValueMatch
from mlscraper.samples import TrainingSet
from mlscraper.scrapers import DictScraper
from mlscraper.scrapers import ListScraper
from mlscraper.scrapers import ValueScraper
from mlscraper.selectors import generate_unique_selectors_for_nodes
from mlscraper.selectors import PassThroughSelector
from more_itertools import first
from more_itertools import flatten
from more_itertools import unzip


class TrainingException(Exception):
    pass


class NoScraperFoundException(TrainingException):
    pass


def get_match_combination_priority(matches):
    if len(matches) == 1:
        return 1

    # check for similarity between matches
    return mean(m1.get_similarity_to(m2) for m1, m2 in combinations(matches, 2))


def train_scraper(training_set: TrainingSet, complexity=100):
    """
    Train a scraper able to extract the given training data.
    """

    logging.info(f"training {training_set=}")

    logging.info(
        "number of matches found per sample: %s",
        [(s, len(s.get_matches())) for s in training_set.item.samples],
    )

    sample_matches = [
        sorted(s.get_matches(), key=lambda m: m.span)[:100]
        for s in training_set.item.samples
    ]
    match_combinations = list(product(*sample_matches))
    logging.info(f"Trying {len(match_combinations)=}")

    # to train quicker, we'll start with combinations that have a high depth
    # this prefers matches, that have a deep root
    # and are thus closer to each other
    match_combinations_prioritized = sorted(
        match_combinations, key=get_match_combination_priority, reverse=True
    )

    for match_combination in match_combinations_prioritized:
        progress_ratio = match_combinations_prioritized.index(match_combination) / len(
            match_combinations_prioritized
        )
        logging.info(f"progress {progress_ratio}")
        try:
            logging.info(f"trying to train scraper for matches ({match_combination=})")
            roots = [s.page for s in training_set.item.samples]
            scraper = train_scraper_for_matches(match_combination, roots, complexity)
            return scraper
        except NoScraperFoundException:
            logging.exception(
                "no scraper found "
                "for complexity and match_combination "
                f"({complexity=}, {match_combination=})"
            )
    raise NoScraperFoundException("did not find scraper")


def train_scraper_for_matches(matches, roots, complexity: int):
    """
    Train a scraper that finds the given matches from the given roots.
    :param matches: the matches to scrape
    :param roots: the root elements containing the matches, e.g. pages or elements on pages
    :param complexity: the complexity to try
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

    if any(c1.has_overlap(c2) for c1, c2 in combinations(matches, 2)):
        raise NoScraperFoundException("a pair of matches overlaps, most likely invalid")

    if found_type == ValueMatch:
        logging.info("training ValueScraper")
        matches: list[ValueMatch]

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
        else:
            logging.info(
                "no early return: %s",
                [(m.node, r, m.node == r) for m, r in zip(matches, roots)],
            )

        selector = first(
            generate_unique_selectors_for_nodes(
                [m.node for m in matches], roots, complexity
            ),
            None,
        )
        if not selector:
            logging.info(f"did not find selector for matches ({matches=})")
            raise NoScraperFoundException(f"no selector found {matches=}")
        logging.info(f"found selector for ValueScraper ({selector=})")
        return ValueScraper(selector, extractor)
    elif found_type == DictMatch:
        logging.info("training DictScraper")
        matches: list[DictMatch]

        # what if some matches have missing keys? idk
        # by using union of all keys, we'll get errors two lines below to be sure
        keys = set(flatten(m.match_by_key.keys() for m in matches))

        # train scraper for each key of dict
        # matches are the matches for the keys
        # roots are the original roots(?)
        scraper_per_key = {}
        for k in keys:
            # todo we get the same match combinations repeatedly
            #  maybe caching uniquely_selects helps
            #  but it is better to store the actual scraper
            logging.info(f"training key for DictScraper ({k=})")
            matches_per_key = [m.match_by_key[k] for m in matches]
            logging.info(f"matches for key: {matches_per_key=}")
            try:
                scraper = train_scraper_for_matches(matches_per_key, roots, complexity)
            except NoScraperFoundException as e:
                raise NoScraperFoundException(
                    f"Training DictScraper failed ({k=})"
                ) from e
            scraper_per_key[k] = scraper
        logging.info(f"found DictScraper ({scraper_per_key=})")
        return DictScraper(scraper_per_key)
    elif found_type == ListMatch:
        logging.info("training ListScraper")
        matches: list[ListMatch]
        logging.info(matches)

        # so we have a list of ListMatch objects
        # we have to find a selector that uniquely matches the list elements
        # todo can be one of the parents
        # for each match, generate all the nodes of list items
        list_item_match_and_roots = [
            (im, r) for m, r in zip(matches, roots) for im in m.matches
        ]
        list_item_nodes_and_roots = [
            (im.root, r) for im, r in list_item_match_and_roots
        ]
        item_nodes, item_roots = unzip(list_item_nodes_and_roots)

        # first selector is fine as it matches perfectly
        # no need to try other selectors
        # -> item_scraper would be the same
        selector = first(
            generate_unique_selectors_for_nodes(
                list(item_nodes), list(item_roots), complexity
            ),
            None,
        )
        if selector:
            logging.info(f"selector that matches list items found ({selector=})")
            # so we have found a selector that matches the list items
            # we now need a scraper, that scrapes each contained item
            # todo im.root does not hold for all items, could be a parent
            item_matches_and_item_roots = [
                (im, im.root) for im, r in list_item_match_and_roots
            ]
            logging.info(
                f"training to extract list items now ({item_matches_and_item_roots})"
            )
            item_matches, item_roots = unzip(item_matches_and_item_roots)
            item_scraper = train_scraper_for_matches(
                list(item_matches), list(item_roots), complexity
            )
            return ListScraper(selector, item_scraper)
        else:
            raise NoScraperFoundException()
    else:
        raise RuntimeError(f"type not matched: {found_type}")
