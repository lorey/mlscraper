import pytest
from mlscraper.html import Page
from mlscraper.matches import TextValueExtractor
from mlscraper.samples import Sample
from mlscraper.samples import TrainingSet
from mlscraper.scrapers import ListScraper
from mlscraper.scrapers import ValueScraper
from mlscraper.selectors import CssRuleSelector
from mlscraper.selectors import PassThroughSelector
from mlscraper.training import train_scraper


def test_train_scraper_simple_list():
    training_set = TrainingSet()
    page = Page(b"<html><body><p>a</p><i>noise</i><p>b</p><p>c</p></body></html>")
    sample = Sample(
        page,
        ["a", "b", "c"],
    )
    training_set.add_sample(sample)
    scraper = train_scraper(training_set)

    # check list scraper
    assert isinstance(scraper, ListScraper)
    assert isinstance(scraper.selector, CssRuleSelector)
    assert scraper.selector.css_rule == "p"

    # check item scraper
    item_scraper = scraper.scraper
    assert isinstance(item_scraper, ValueScraper)
    assert isinstance(item_scraper.selector, PassThroughSelector)
    assert isinstance(item_scraper.extractor, TextValueExtractor)


def test_train_scraper_list_of_dicts():
    html = b"""
    <html>
    <body>
    <div><p>a</p><p>b</p></div>
    <div><p>c</p><p>d</p></div>
    </body>
    </html
    """
    page = Page(html)
    sample = Sample(page, [["a", "b"], ["c", "d"]])
    training_set = TrainingSet()
    training_set.add_sample(sample)
    scraper = train_scraper(training_set)
    assert isinstance(scraper, ListScraper)
    assert isinstance(scraper.selector, CssRuleSelector)
    assert scraper.selector.css_rule == "div"

    inner_scraper = scraper.scraper
    assert isinstance(inner_scraper, ListScraper)
    assert isinstance(inner_scraper.selector, CssRuleSelector)
    assert inner_scraper.selector.css_rule == "p"

    value_scraper = inner_scraper.scraper
    assert isinstance(value_scraper, ValueScraper)
    assert isinstance(value_scraper.selector, PassThroughSelector)
    assert isinstance(value_scraper.extractor, TextValueExtractor)


def test_train_scraper_stackoverflow(stackoverflow_samples):
    training_set = TrainingSet()
    for s in stackoverflow_samples:
        training_set.add_sample(s)

    scraper = train_scraper(training_set)
    assert isinstance(scraper, ListScraper)
    assert isinstance(scraper.selector, CssRuleSelector)

    scraping_result = scraper.get(stackoverflow_samples[0].page)
    scraping_sample = stackoverflow_samples[0].value
    assert scraping_result == scraping_sample
