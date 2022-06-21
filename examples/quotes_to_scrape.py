import logging

import requests
from mlscraper.html import Page
from mlscraper.samples import Sample, TrainingSet
from mlscraper.training import train_scraper


def main():
    """
    This example shows you how to build a scraper for authors on quotes.toscrape.com
    """

    # fetch the page to train
    einstein_url = 'http://quotes.toscrape.com/author/Albert-Einstein/'
    resp = requests.get(einstein_url)
    assert resp.status_code == 200

    # create a sample for Albert Einstein
    training_set = TrainingSet()
    page = Page(resp.content)
    sample = Sample(page, {'name': 'Albert Einstein', 'born': 'March 14, 1879'})
    training_set.add_sample(sample)

    # train the scraper with the created training set
    scraper = train_scraper(training_set)

    # scrape another page
    resp = requests.get('http://quotes.toscrape.com/author/J-K-Rowling')
    result = scraper.get(Page(resp.content))
    print(result)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
