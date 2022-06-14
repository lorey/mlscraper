import pytest
from mlscraper.html import Page
from mlscraper.samples import Sample


@pytest.fixture(scope="module")
def stackoverflow_samples():
    with open("tests/static/so.html", "rb") as file:
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
