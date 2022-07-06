from mlscraper.html import Page
from mlscraper.selectors import CssRuleSelector
from mlscraper.selectors import generate_unique_selectors_for_nodes


def _get_css_selectors_for_nodes(nodes):
    """
    helper to extract plain css rules
    """
    return [
        selector.css_rule
        for selector in generate_unique_selectors_for_nodes(nodes, None, 100)
        if isinstance(selector, CssRuleSelector)
    ]


class TestGenerateUniqueSelectorsForNodes:
    def test_basic(self):
        page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
        page1 = Page(page1_html)

        page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
        page2 = Page(page2_html)

        nodes = list(map(lambda p: p.select("p.test")[0], [page1, page2]))
        selectors_found = _get_css_selectors_for_nodes(nodes)

        assert "p" not in selectors_found, "p is selector but not unique"
        assert "div" not in selectors_found, "div is no common tag"
        assert "body > p.test" not in selectors_found, "body is irrelevant"

        assert ".test" in selectors_found
        assert "p.test" in selectors_found

    def test_nth(self):
        html = b"""<html><body>
        <ul><li>target</li><li>noise</li></ul>
        <ul><li>target</li><li>noise</li></ul>
        </body></html>"""
        page = Page(html)
        first_li_tags = [ul.select("li")[0] for ul in page.select("ul")]
        unique_selectors = _get_css_selectors_for_nodes(first_li_tags)
        assert "li:nth-child(1)" in unique_selectors

    def test_ids(self):
        page = Page(
            b"""
            <html><body>
                <div id="target">test</div>
                <div>irrelevant</div>
            </body></html>"""
        )
        node = page.select("#target")[0]
        selectors = _get_css_selectors_for_nodes([node])
        assert "#target" in selectors

    def test_multi_parents(self):
        # selection requires to pinpoint #target parent
        page = Page(b'<html><body><div id="target"><p>test</p></div><div><p></p></div>')
        node = page.select("#target")[0].select("p")[0]
        selectors = _get_css_selectors_for_nodes([node])
        assert "#target p" in selectors

    def test_itemprop_selector(self):
        html = b"""<html><body>
        <div itemprop="user">lorey</div>
        <div itemprop="user">jonashaag</div>
        </body></html>"""
        page = Page(html)
        elements = page.select("div")
        direct_css_selectors = _get_css_selectors_for_nodes(elements)

        assert "div[itemprop]" in direct_css_selectors
        assert 'div[itemprop="user"]' in direct_css_selectors
