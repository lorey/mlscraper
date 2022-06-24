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


def test_train_scraper_multipage():
    training_set = TrainingSet()
    for items in ["ab", "cd"]:
        html = b"""
        <html><body>
        <div class="target">
        <ul><li>%s</li><li>%s</li></ul>
        </div>
        </body></html>
        """ % (
            items[0].encode(),
            items[1].encode(),
        )
        training_set.add_sample(Sample(Page(html), [items[0], items[1]]))
    scraper = train_scraper(training_set)
    assert scraper.selector.css_rule == "li"
    assert scraper.get(
        Page(b"""<html><body><ul><li>first</li><li>second</li></body></html>""")
    ) == ["first", "second"]


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


GITHUB_PROFILES = {
    "lorey": {
        "name": "Karl Lorey",
        "username": "lorey",
        "location": "Berlin, Germany",
        "url": "https://karllorey.com",
        "company": "@loreyventures",
        "followers": "197",
        "following": "243",
    },
    "jonashaag": {
        "name": "Jonas Haag",
        "username": "jonashaag",
        "location": "Karlsruhe, Germany",
        "url": "https://de.linkedin.com/in/haag",
        "company": "@Quantco",
        "followers": "329",
        "following": "20",
    },
    "siboehm": {
        "name": "Simon Boehm",
        "username": "siboehm",
        "location": "Erlangen, Germany",
        "url": "http://siboehm.com",
        "company": "AMD",
        "followers": "87",
        "following": "27",
    },
}


# @pytest.mark.skip("missing selectors")
def test_train_scraper_github():
    keys_to_test = [
        "name",
        "username",
        "company",
        "location",
        "url",
        "followers",
        "following",
    ]

    def profile_as_page(login):
        with open(f"tests/static/github/{login}.html", "rb") as file:
            return Page(file.read())

    def sample_data_for_profile(login):
        return {k: v for k, v in GITHUB_PROFILES[login].items() if k in keys_to_test}

    training_set = TrainingSet()
    for login in ["lorey", "siboehm"]:
        sample = Sample(profile_as_page(login), sample_data_for_profile(login))
        training_set.add_sample(sample)

    # train
    scraper = train_scraper(training_set)

    login_target = "jonashaag"
    page_target = profile_as_page(login_target)
    assert scraper.get(page_target) == sample_data_for_profile(login_target)
