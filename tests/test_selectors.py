from mlscraper.html import Page
from mlscraper.selectors import generate_selector_for_nodes


def test_generate_selector_for_nodes():
    page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
    page1 = Page(page1_html)

    page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
    page2 = Page(page2_html)

    nodes = list(map(lambda p: p.select("p.test")[0], [page1, page2]))
    gen = generate_selector_for_nodes(nodes, None, 1)
    selectors_found = [sel.css_rule for sel in gen]
    assert {".test", "p.test"} == set(selectors_found)


class TestGenerateSelectorForNodes:
    def test_generate_selector_for_nodes(self):
        # generate_selector_for_nodes()
        pass
