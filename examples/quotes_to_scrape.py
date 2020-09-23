import requests

from mlscraper import SingleItemSample, SingleItemScraper


def main():
    items = {
        "http://quotes.toscrape.com/author/Eleanor-Roosevelt/": {
            "name": "Eleanor Roosevelt",
            "birth": "October 11, 1884",
        },
        "http://quotes.toscrape.com/author/Andre-Gide/": {
            "name": "André Gide",
            "birth": "November 22, 1869",
        },
        "http://quotes.toscrape.com/author/Thomas-A-Edison/": {
            "name": "Thomas A. Edison",
            "birth": "February 11, 1847",
        },
    }
    results = {url: requests.get(url) for url in items.keys()}

    # train scraper
    samples = [
        SingleItemSample(items[url], results[url].content) for url in items.keys()
    ]
    scraper = SingleItemScraper.build(samples)

    print("Scraping Albert Einstein")
    html = requests.get("http://quotes.toscrape.com/author/Albert-Einstein/").content
    result = scraper.scrape(html)

    print("Result: %s" % result)
    # > Result: {'birth': 'March 14, 1879', 'name': 'Albert Einstein'}


if __name__ == "__main__":
    main()
