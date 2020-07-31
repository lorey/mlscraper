import os

import pytest

from autoscraper import (
    MultiItemScraper,
    MultiItemSamples,
    SingleItemScraper,
    SingleItemSample,
)


def read_file(relative_path):
    file_path = os.path.join(os.path.dirname(__file__), relative_path)
    with open(file_path) as file:
        html = file.read()
    return html


@pytest.fixture
def single_basic_train_html():
    return read_file(os.path.join("static", "single", "basic", "train.html"))


@pytest.fixture
def multi_single_result_page_html():
    return read_file(os.path.join("static", "multi", "single-result-page.html"))


def test_multi(multi_single_result_page_html):
    items = [
        {"title": "One great result!", "description": "Some description"},
        {"title": "Another great result!", "description": "Another description"},
        {"title": "Result to be found", "description": "Description to crawl"},
    ]

    html = multi_single_result_page_html
    scraper = MultiItemScraper.build(MultiItemSamples(items, html))
    assert scraper.scrape(html) == items

    # optional since they're only human guesses
    assert ".result-single" in scraper.parent_selector
    assert scraper.value_selectors == {"title": "h2", "description": "p"}


def test_single(single_basic_train_html):
    data = {"name": "Peter", "description": "Cool-looking guy"}
    samples = [SingleItemSample(data, single_basic_train_html)]
    scraper = SingleItemScraper.build(samples)
    result = scraper.scrape(single_basic_train_html)
    assert result == data
