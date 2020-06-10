import os

from autoscrape import MultiItemScraper


def test_extraction():
    items = [
        {"title": "One great result!", "description": "Some description"},
        {"title": "Another great result!", "description": "Another description"},
        {"title": "Result to be found", "description": "Description to crawl"},
    ]

    file_path = os.path.join(
        os.path.dirname(__file__), "static/single-result-page.html"
    )
    with open(file_path) as file:
        html = file.read()

    scraper = MultiItemScraper.build(html, items)
    assert scraper.scrape(html) == items

    # optional since they're only human guesses
    assert ".result-single" in scraper.parent_selector
    assert scraper.value_selectors == {"title": "h2", "description": "p"}
