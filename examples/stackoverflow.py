import logging

import requests

from mlscraper import SingleItemPageSample, RuleBasedSingleItemScraper


def main():
    items = {
        "https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array": {
            "title": "Why is processing a sorted array faster than processing an unsorted array?"
        },
        "https://stackoverflow.com/questions/927358/how-do-i-undo-the-most-recent-local-commits-in-git": {
            "title": "How do I undo the most recent local commits in Git?"
        },
        "https://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do": {
            "title": "What does the “yield” keyword do?"
        },
    }

    results = {url: requests.get(url) for url in items.keys()}

    # train scraper
    samples = [
        SingleItemPageSample(results[url].content, items[url]) for url in items.keys()
    ]
    scraper = RuleBasedSingleItemScraper.build(samples)

    print("Scraping new question")
    html = requests.get(
        "https://stackoverflow.com/questions/2003505/how-do-i-delete-a-git-branch-locally-and-remotely"
    ).content
    result = scraper.scrape(html)

    print("Result: %s" % result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
