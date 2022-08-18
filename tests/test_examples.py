from examples.quotes_to_scrape import main as quotes_to_scrape_main

# Example 1 - Quotes to scrape
def test_example_quotes_to_scrape():
    '''
    Test if the example quotes_to_scrape.py works
    '''

    assert quotes_to_scrape_main() == \
       {'name': 'J.K. Rowling', 'born': 'July 31, 1965'}, \
       'Quotes to scrape example failed'
