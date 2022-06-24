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
