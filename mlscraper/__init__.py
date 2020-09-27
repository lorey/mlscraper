__author__ = """Karl Lorey"""
__email__ = "git@karllorey.com"
__version__ = "0.1.1"

import logging
import random
import re
from collections import Counter
from itertools import chain
from typing import List

import pandas as pd
from bs4 import BeautifulSoup
from more_itertools import flatten

from mlscraper.ml import NodePreprocessing, train_pipeline
from mlscraper.parser import make_soup_page, ExtractionResult
from mlscraper.training import SingleItemPageSample, MultiItemPageSample
from mlscraper.util import (
    get_common_ancestor_for_paths,
    get_common_ancestor_for_nodes,
    get_tree_path,
    generate_css_selectors_for_node,
    get_selectors,
    derive_css_selector,
    generate_path_selectors,
    generate_unique_path_selectors,
)


def create_single_item_samples(url_to_item):
    """
    Creates single page training data for you.

    :param url_to_item: dict with url as key and expected dict as value
    :return: samples
    """
    import requests

    results = {url: requests.get(url) for url in url_to_item.keys()}
    assert all(resp.status_code == 200 for resp in results.values())

    pages = {url: make_soup_page(results[url].content) for url in url_to_item.keys()}

    # train scraper
    samples = []
    for url in url_to_item:
        page = pages[url]
        item = url_to_item[url]

        # use random sample if found several times to try to get all possible selectors
        item_extraction = {
            k: ExtractionResult(random.choice(page.find(v))) for k, v in item.items()
        }
        sample = SingleItemPageSample(page, item_extraction)
        samples.append(sample)
    return samples


class RuleBasedSingleItemScraper:
    """A simple scraper that will simply try to infer the best css selectors."""

    def __init__(self, classes_per_attr):
        self.classes_per_attr = classes_per_attr

    @staticmethod
    def build(samples: List[SingleItemPageSample]):
        attributes = set(flatten(s.item.keys() for s in samples))

        rules = {}  # attr -> selector
        for attr in attributes:
            logging.info("Training attribute %s" % attr)

            # get all potential matches
            matching_nodes = flatten([s.page.find(s.item[attr]) for s in samples])
            # since uniqueness requires selection over and over, we don't use generate_unique_path... here
            path_selector_generator = (
                generate_path_selectors(node._soup_node) for node in matching_nodes
            )
            selectors = set(chain(*path_selector_generator))

            # check if they are unique on every page
            # -> for all potential selectors: compute score
            selector_scoring = {}  # selector -> score
            for i, selector in enumerate(selectors):
                if selector not in selector_scoring:
                    logging.info("testing %s (%d/%d)", selector, i, len(selectors))
                    matches_per_page = (s.page.select(selector) for s in samples)
                    matches_per_page_right = [
                        len(m) == 1 and m[0].get_text() == s.item[attr]
                        for m, s in zip(matches_per_page, samples)
                    ]
                    score = sum(matches_per_page_right) / len(samples)
                    selector_scoring[selector] = score

            # find the selector with the best coverage, i.e. the highest accuracy
            logging.info("Scoring for %s: %s", attr, selector_scoring)
            # sort by score (desc) and selector length (asc)
            selectors_sorted = sorted(
                selector_scoring.items(), key=lambda x: (x[1], -len(x[0])), reverse=True
            )
            logging.info("Best scores for %s: %s", attr, selectors_sorted[:3])
            try:
                selector_best = selectors_sorted[0][0]
                if selector_scoring[selector_best] < 1:
                    logging.warning(
                        "Best selector for %s does not work for all samples (score is %f)"
                        % (attr, selector_scoring[selector_best])
                    )

                rules[attr] = selector_best
            except IndexError:
                logging.warning("No selector found for %s", attr)
        print(rules)
        return RuleBasedSingleItemScraper(rules)

    def scrape(self, html):
        page = make_soup_page(html)
        item = {
            k: page.select(self.classes_per_attr[k])[0].get_text()
            for k in self.classes_per_attr.keys()
        }
        return item


class SingleItemScraper:
    def __init__(self, classifiers, min_match_proba=0.7):
        self.classifiers = classifiers
        self.min_match_proba = min_match_proba

    @staticmethod
    def build(samples: List[SingleItemPageSample]):
        """
        Build a scraper by inferring rules.

        :param samples: Samples to train
        :return: the scraper
        """

        # parse html
        soups = [sample.page._soup for sample in samples]

        # find samples on the pages
        matches = []
        for sample, soup in zip(samples, soups):
            matches_per_item = {}
            for key in sample.item.keys():
                needle = sample.item[key]

                # currently, we can only find strings with .text extraction
                assert isinstance(needle, str), "Only strings supported"

                # search for text, check if parent returns this text
                text_matches = soup.find_all(text=re.compile(needle))
                logging.debug("Matches for %s: %s", needle, text_matches)
                text_parents = (ns.parent for ns in text_matches)
                tag_matches = [p for p in text_parents if extract_text(p) == needle]
                matches_per_item[key] = tag_matches
            matches.append(matches_per_item)
        # print(matches)

        matches_unique = []
        for matches_item, sample in zip(matches, samples):
            if all(len(matches_item[attr]) == 1 for attr in sample.item.keys()):
                matches_item_unique = {
                    attr: matches_item[attr][0] for attr in sample.item.keys()
                }
                matches_unique.append(matches_item_unique)
            else:
                logging.warning(
                    "Sample values not unique on page, discarding: %s -> %s"
                    % (sample, matches_item)
                )
                matches_unique.append(None)
        # print(matches_unique)

        # for each attribute:
        attributes = set(flatten(sample.item.keys() for sample in samples))
        print(attributes)
        classifiers = {}
        for attr in attributes:
            print(attr)
            # 1. take all items with unique samples
            # 2. mark nodes that match sample as true, others as false
            training_data = []
            for matches_item, soup in zip(matches_unique, soups):
                if matches_item:
                    node_to_find = matches_item[attr]
                    training_data.extend(
                        [(node, node == node_to_find) for node in soup.descendants]
                    )
                else:
                    logging.warning("Skipping one sample for %s" % attr)

            # 3. train classifier
            df = pd.DataFrame(training_data, columns=["node", "target"])
            if len(df[df["target"] == False]) > 100:
                df_train = pd.concat(
                    [
                        df[df["target"] == True],
                        df[df["target"] == False].sample(frac=0.01),
                    ]
                )
            else:
                df_train = df

            pipeline = train_pipeline(df_train["node"], df_train["target"])
            # pipeline = train_pipeline(df["node"], df["target"])
            classifiers[attr] = pipeline

        return SingleItemScraper(classifiers)

    def scrape(self, html):
        soup = BeautifulSoup(html, "lxml")

        # data is a dict, because page is one item
        data = {}

        nodes = list(soup.descendants)
        for attr in self.classifiers.keys():
            # predict proba of all nodes
            node_predictions = self.classifiers[attr].predict_proba(nodes)

            # turn it into a data frame
            df = pd.DataFrame(node_predictions, columns=["is_noise", "is_target"])

            # re-add nodes to extract them later
            df["node"] = pd.Series(nodes)

            # get best match
            df_nodes_by_proba = df.sort_values("is_target", ascending=False)
            best_match = df_nodes_by_proba.iloc[0]

            # use if probability > threshold
            if best_match["is_target"] > self.min_match_proba:
                # todo apply extractor based on attribute (.text, attrs[href], etc.)
                data[attr] = extract_text(best_match["node"])
            else:
                logging.warning(
                    "%s not found in html, probability %f < %f",
                    attr,
                    best_match["is_target"],
                    self.min_match_proba,
                )
        # return the data dictionary
        return data


def extract_text(node):
    return node.text.strip()


class MultiItemScraper:
    """
    Extracts several items from a single page, e.g. all results from a page of search results.
    """

    def __init__(self, parent_selector, value_selectors):
        self.parent_selector = parent_selector
        self.value_selectors = value_selectors

    @staticmethod
    def build(samples: List[MultiItemPageSample]):
        """
        Build the scraper by inferring rules.
        """
        assert len(samples) == 1, "can only train with one sample"

        items = samples[0].items

        # observation:
        # - if multiple common distinctive ancestors exist,
        #   one can choose the ones easier to match, as this will not affect later value selection

        # assumptions:
        # - all samples given must be all samples that can be found on a page
        #   -> much easier evaluation because we can detect false positives
        # - for each sample, there's at least one distinct ancestor containing only this sample
        #   -> will fail for inline results but allow for much easier selector generation
        # - there won't be too many duplicate values so we can ignore samples that contain them
        #   -> makes ancestor computation much easier by increasing false positives

        # glossary
        # - ancestors: the path of elements in the DOM from root to a specific element

        soup = samples[0].page._soup

        # 1. find all examples on the site
        matches = []
        for item in items:
            matches_item = {}
            for key, value in item.items():
                elements_with_value = soup.find_all(text=value)
                print("{}: {}".format(key, elements_with_value))
                matches_item[key] = elements_with_value
            matches.append(matches_item)
        print(matches)

        # 1.1 exclude duplicate samples for now to avoid errors
        #     (e.g. 2018 existing 4x on a site)
        matches_unique = []
        for item, matches_item in zip(items, matches):
            multiple_occurence_keys = [
                k for k in matches_item if len(matches_item[k]) != 1
            ]
            if not multiple_occurence_keys:
                matches_unique.append({k: v[0] for k, v in matches_item.items()})
            else:
                matches_unique.append(None)
                error = "Item %r dropped because attribute(s) %r were found several times on page"
                logging.warning(error, item, multiple_occurence_keys)
        print(matches_unique)

        # 2. extract the distinct ancestors for each sample (one sample, one ancestor)
        # 2.1 find deepest common ancestor of each item
        deepest_common_ancestor_per_item = [
            get_common_ancestor_for_nodes([node for node in match.values()])
            for match in matches_unique
        ]
        print(deepest_common_ancestor_per_item)
        assert len(set(deepest_common_ancestor_per_item)) == len(
            deepest_common_ancestor_per_item
        )

        # 2.2 get a list of distinctive ancestors for each item
        deepest_common_ancestor_of_items = get_common_ancestor_for_nodes(
            deepest_common_ancestor_per_item
        )
        print(deepest_common_ancestor_of_items)

        tree_paths = [get_tree_path(node) for node in deepest_common_ancestor_per_item]
        unique_ancestors_per_item = []
        for tree_path_of_item in tree_paths:
            uniques = [
                node
                for node in tree_path_of_item
                if not any(node in tp for tp in tree_paths if tp != tree_path_of_item)
            ]
            unique_ancestors_per_item.append(uniques)

        # 3. find a selector to match exactly one distinctive ancestor for each sample
        ancestor_selector = derive_css_selector(unique_ancestors_per_item, soup)
        if not ancestor_selector:
            raise RuntimeError("Found no selector")
        print(ancestor_selector)

        # select all ancestors on the page
        ancestors = soup.select(ancestor_selector)

        # 4. find simplest selector from these distinctive ancestors to the sample values
        value_selectors = {}
        for attr in set([attr for item in items for attr in item.keys()]):
            # try to infer a rule that matches attribute for most items given the selector

            # compute value nodes and resp. ancestor nodes
            value_nodes = [match[attr].parent for match in matches_unique]
            value_parents = [
                next(iter(set(value_node.parents).intersection(ancestors)))
                for value_node in value_nodes
            ]
            print(value_nodes)
            print(value_parents)

            # get all potential candidates for value selectors
            value_selector_cand = [
                list(get_selectors(node, parent))
                for node, parent in zip(value_nodes, value_parents)
            ]

            # merge all selector candidates and find the most common one
            value_selector = Counter(flatten(value_selector_cand)).most_common(1)[0][0]
            value_selectors[attr] = value_selector
        print(value_selectors)

        return MultiItemScraper(ancestor_selector, value_selectors)

    def scrape(self, html):
        data = []

        soup = BeautifulSoup(html, "lxml")
        ancestors = soup.select(self.parent_selector)
        for ancestor in ancestors:
            data_single = {
                attr: ancestor.select(selector)[0].text.strip()
                for attr, selector in self.value_selectors.items()
            }
            data.append(data_single)
        return data
