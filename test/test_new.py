from mlscraper import RuleBasedSingleItemScraper, SingleItemPageSample


def test_basic():
    html = '<html><body><div class="parent"><p class="item">result</p></div><p class="item">not a result</p></body></html>'
    item = {"res": "result"}

    samples = [SingleItemPageSample(html, item)]
    scraper = RuleBasedSingleItemScraper.build(samples)
    assert scraper.scrape(html) == item
