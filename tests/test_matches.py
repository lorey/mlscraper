from mlscraper.html import Page
from mlscraper.matches import AttributeValueExtractor
from mlscraper.matches import generate_all_value_matches
from mlscraper.matches import is_dimensions_match
from mlscraper.matches import ValueMatch


def test_is_dimensions_match_plain():
    extractor = AttributeValueExtractor("height")
    value_match = ValueMatch(None, extractor)
    assert is_dimensions_match(value_match)


def test_is_dimensions_match_generation():
    page = Page(b'<html><body><img height="20" width="20"</body></html>')
    matches_unfiltered = list(generate_all_value_matches(page, "20"))
    assert matches_unfiltered
    matches = [m for m in matches_unfiltered if not is_dimensions_match(m)]
    assert not matches


def test_attribute_extractor():
    html_ = (
        b'<html><body><a href="https://karllorey.com"></a><a>no link</a></body></html>'
    )
    page = Page(html_)
    extractor = AttributeValueExtractor("href")
    a_tags = page.select("a")
    assert extractor.extract(a_tags[0]) == "https://karllorey.com"
    assert extractor.extract(a_tags[1]) is None


def test_extractor_equality():
    # we want to make sure that each extractor exists only once
    # as we need this to ensure extractor selection
    e1 = AttributeValueExtractor("href")
    e2 = AttributeValueExtractor("href")
    assert e1 == e2
    assert len({e1, e2}) == 1
