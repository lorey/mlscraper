from mlscraper import RuleBasedSingleItemScraper, SingleItemPageSample
from mlscraper.parser import make_soup_page


def test_basic():
    html = '<html><body><div class="parent"><p class="item">result</p></div><p class="item">not a result</p></body></html>'
    page = make_soup_page(html)
    item = {"res": "result"}

    samples = [SingleItemPageSample(page, item)]
    scraper = RuleBasedSingleItemScraper.build(samples)
    assert scraper.scrape(html) == item
