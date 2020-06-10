# Scrape HTML automatically with autoscrape
Many services for crawling and scraping automation allow you to select data in a browser and get JSON results in return.
No need to specify CSS selectors or anything else.

I've been wondering for a long time why there's no Open Source solution that does something like this.
So here's my attempt at creating a python library to enable automatic scraping.

All you have to do is define some examples of scraped data.
autoscrape will figure out everything else and return clean data.

Currently, this is a proof of concept with a simplistic solution.

## How it works
After you've defined the data you want to scrape, autoscrape will:

- find your examples inside HTML
- determine which rules to apply for extraction
- extract the data for you with these rules

```python
# the items found on the training page
items = [
    {"title": "One great result!", "description": "Some description"},
    {"title": "Another great result!", "description": "Another description"},
    {"title": "Result to be found", "description": "Description to crawl"},
]

# training the scraper with the items
scraper = MultiItemScraper.build(training_html, items)
scraper.scrape(training_html)  # will produce the items above
scraper.scrape(new_html)  # will apply the learned rules and extract new items
```


## Related work
- Learning to extract hierarchical information from semi-structured documents: http://ftp.cse.buffalo.edu/users/azhang/disc/disc01/cd1/out/papers/cikm/p250.pdf
- WHISK: Extraction of structured and unstructured information: https://www.cis.uni-muenchen.de/~yeong/Kurse/ws0809/WebDataMining/whisk.pdf