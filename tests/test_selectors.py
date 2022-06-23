from mlscraper.html import Page
from mlscraper.selectors import _generate_direct_css_selectors_for_nodes
from mlscraper.selectors import generate_unique_selectors_for_nodes


def get_css_selectors_for_node(node):
    """
    helper to extract plain css rules
    """
    return [
        selector.css_rule
        for selector in generate_unique_selectors_for_nodes([node], None, 100)
    ]


class TestGenerateUniqueSelectorsForNodes:
    def test_basic(self):
        page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
        page1 = Page(page1_html)

        page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
        page2 = Page(page2_html)

        nodes = list(map(lambda p: p.select("p.test")[0], [page1, page2]))
        gen = generate_unique_selectors_for_nodes(nodes, None, 1)
        selectors_found = [sel.css_rule for sel in gen]

        assert "p" not in selectors_found
        assert "div" not in selectors_found

        assert ".test" in selectors_found
        assert "p.test" in selectors_found
        assert "body > p.test" in selectors_found

    def test_nth(self):
        html = b"""<html><body>
        <ul><li>target</li><li>noise</li></ul>
        <ul><li>target</li><li>noise</li></ul>
        </body></html>"""
        page = Page(html)
        first_li_tags = [ul.select("li")[0] for ul in page.select("ul")]
        unique_selectors = [
            s.css_rule
            for s in generate_unique_selectors_for_nodes(first_li_tags, None, 100)
        ]
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
        selectors = get_css_selectors_for_node(node)
        assert "#target" in selectors

    def test_multi_parents(self):
        page = Page(b'<html><body><div id="target"><p>test</p></div><div><p></p></div>')
        node = page.select("#target")[0].select("p")[0]
        selectors = get_css_selectors_for_node(node)
        assert "#target p" in selectors


class TestGenerateDirectCssSelectorsForNodes:
    def test_itemprop_selector(self):
        html = b"""<html><body>
        <div itemprop="user">lorey</div>
        <div itemprop="user">jonashaag</div>
        </body></html>"""
        page = Page(html)
        direct_css_selectors = list(
            _generate_direct_css_selectors_for_nodes(page.select("div"))
        )

        assert "div[itemprop]" in direct_css_selectors
        assert 'div[itemprop="user"]' in direct_css_selectors

    def test_nth(self):
        html = b"""<html><body>
        <ul><li>target</li><li>noise</li></ul>
        <ul><li>target</li><li>noise</li></ul>
        </body></html>"""
        page = Page(html)
        first_li_tags = [ul.select("li")[0] for ul in page.select("ul")]
        unique_selectors = list(_generate_direct_css_selectors_for_nodes(first_li_tags))
        assert "li:nth-child(1)" in unique_selectors
