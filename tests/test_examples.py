import os

import pytest

PYTEST_SKIP_EXAMPLES = os.environ.get("PYTEST_SKIP_EXAMPLES", "1")


@pytest.mark.skipif(PYTEST_SKIP_EXAMPLES == "1", reason=f'"{PYTEST_SKIP_EXAMPLES=}"')
def test_example_quotes_to_scrape():
    """
    Test if the example quotes_to_scrape.py works
    """
    from examples.quotes_to_scrape import main as quotes_to_scrape_main

    assert quotes_to_scrape_main() == {
        "name": "J.K. Rowling",
        "born": "July 31, 1965",
    }, "Quotes to scrape example failed"
