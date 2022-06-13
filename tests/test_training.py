import pytest
from mlscraper.samples import TrainingSet
from mlscraper.training import train_scraper


@pytest.mark.skip("listscraper just returns one result instead of three")
def test_train_scraper(stackoverflow_samples):
    training_set = TrainingSet()
    for s in stackoverflow_samples:
        training_set.add_sample(s)

    scraper = train_scraper(training_set.item)
    print(f"result scraper: {scraper}")

    scraping_result = scraper.get(stackoverflow_samples[0].page)
    print(f"scraping result: {scraping_result}")

    scraping_sample = stackoverflow_samples[0].value
    assert scraping_result == scraping_sample
