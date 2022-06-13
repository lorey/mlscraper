import pytest

from mlscraper.samples import ItemStructureException, Sample, make_training_set
from mlscraper.util import DictMatch, ListMatch, Page


class TestTrainingSet:
    def test_make_training_set(self):
        pages = [Page(""), Page("")]
        items = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
        make_training_set(pages, items)

    def test_make_training_set_error(self):
        pages = [Page(""), Page("")]
        items = [{"a": "1", "b": "2"}, {"a": "3", "b": []}]
        with pytest.raises(ItemStructureException):
            make_training_set(pages, items)


class TestMatch:
    def test_get_matches_dict_basic(self):
        page_html = "<html><body><h1>test</h1><p>2010</p><div class='footer'>2010</div></body></html>"
        s = Sample(Page(page_html), {"h": "test", "year": "2010"})
        matches = s.get_matches()
        assert len(matches) == 2
        assert all(isinstance(m, DictMatch) for m in matches)

    def test_get_matches_list_basic(self):
        item_htmls = map(lambda i: f"<li>{i}</li>", [1, 2, 2, 4])
        body_html = f"<ul>{''.join(item_htmls)}</ul>"
        page_html = f"<html><body>{body_html}</body></html>"
        page = Page(page_html)
        sample = Sample(page, ["1", "2", "2", "4"])
        matches = sample.get_matches()

        # todo check duplicate generation
        # assert len(matches) == 2
        assert all(isinstance(m, ListMatch) for m in matches)

    def test_get_matches_list_of_dicts(self):
        page_html = (
            "<html><body>"
            '<div><p class="title">Herr</p><p class="name">Lorey</p></div> '
            '<div><p class="title">Frau</p><p class="name">Müller</p></div> '
            "</body></html>"
        )
        page = Page(page_html)
        sample = Sample(
            page,
            [{"title": "Herr", "name": "Lorey"}, {"title": "Frau", "name": "Müller"}],
        )
        matches = sample.get_matches()

        # check that matches returns one possible list match
        assert len(matches) == 1

        # check that matched list item is dict
        match = matches[0]
        assert isinstance(match, ListMatch)
        assert len(match.matches) == 2
        assert all(isinstance(m, DictMatch) for m in match.matches)
        print(match.get_root())
        print(match.get_span())
