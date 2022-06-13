import pytest
from mlscraper.samples import make_training_set
from mlscraper.training import train_scraper
from mlscraper.util import Page


@pytest.fixture
def stackoverflow_training_set():
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
    return make_training_set([page], [item])


@pytest.mark.skip("takes too long")
def test_train_scraper(stackoverflow_training_set):
    train_scraper(stackoverflow_training_set.item)
