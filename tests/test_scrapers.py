import pytest

from mlscraper.samples import Sample
from mlscraper.scrapers import DictScraper, ListScraper, ValueScraper
from mlscraper.selectors import CssRuleSelector
from mlscraper.util import AttributeValueExtractor, Page, TextValueExtractor


@pytest.fixture
def stackoverflow_samples():
    with open("tests/static/so.html") as file:
        page = Page(file.read())

    item = [
        {
            "user": "/users/624900/jterrace",
            "upvotes": "20",
            "when": "2011-06-16 19:45:11Z",
        },
        {
            "user": "/users/4044167/nico-knoll",
            "upvotes": "16",
            "when": "2017-09-06 15:27:16Z",
        },
        {
            "user": "/users/1275778/lorey",
            "upvotes": "0",
            "when": "2021-01-06 10:50:04Z",
        },
    ]
    samples = [Sample(page, item)]
    return samples


class TestListOfDictScraper:
    def test_scrape(self, stackoverflow_samples):
        user_scraper = ValueScraper(
            CssRuleSelector(".user-details a"), AttributeValueExtractor("href")
        )
        upvotes_scraper = ValueScraper(
            CssRuleSelector(".js-vote-count"), TextValueExtractor()
        )
        when_scraper = ValueScraper(
            CssRuleSelector(".user-action-time span"), AttributeValueExtractor("title")
        )
        scraper_per_key = {
            "user": user_scraper,
            "upvotes": upvotes_scraper,
            "when": when_scraper,
        }
        scraper = DictScraper(scraper_per_key)

        selector = CssRuleSelector(".answer")
        ls = ListScraper(selector, scraper)
        sample = stackoverflow_samples[0]
        results = ls.get(sample.page)
        assert sample.value == results


class TestDictScraper:
    def test_scrape_matches(self):
        item = {"h": "no 1", "t": "the first one"}

        elem_temp = "<div><h1>%(h)s</h1><p>%(t)s</p></div>"
        elem = elem_temp % item
        html = f"<html><body>{elem}</body></html>"
        page = Page(html)
        text_extractor = TextValueExtractor()
        ds = DictScraper(
            scraper_per_key={
                "h": ValueScraper(CssRuleSelector("h1"), text_extractor),
                "t": ValueScraper(CssRuleSelector("p"), text_extractor),
            }
        )
        assert ds.get(page) == item


class TestValueScraper:
    def test_value_scraper(self):
        page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
        page1 = Page(page1_html)

        page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
        page2 = Page(page2_html)

        vs = ValueScraper(CssRuleSelector(".test"), TextValueExtractor())
        assert vs.get(page1) == "test"
        assert vs.get(page2) == "hallo"
