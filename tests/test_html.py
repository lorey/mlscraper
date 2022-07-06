from mlscraper.html import get_relative_depth
from mlscraper.html import get_root_node
from mlscraper.html import HTMLExactTextMatch
from mlscraper.html import Page


def test_get_root_nodes():
    html = b'<html><body><div><p id="one"></p><p><span id="two"></span></p></div></body></html>'
    page = Page(html)
    node_1 = page.select("#one")[0]
    node_2 = page.select("#two")[0]
    root = get_root_node([node_1, node_2])
    assert root == page.select("div")[0]


def test_node_parents():
    html = b'<html><body><div><p id="one"></p><p><span id="two"></span></p></div></body></html>'
    page = Page(html)
    assert page.select("html")[0].parent == page, "html's parent should be page"


def test_node_ancestors():
    html = b'<html><body><div><p id="one"></p><p><span id="two"></span></p></div></body></html>'
    page = Page(html)
    element = page.select("#one")[0]
    ancestors = element.ancestors
    assert ancestors[0] == element.parent, "first ancestor should be parent"
    assert isinstance(ancestors[-1], Page), "last ancestor should be page"


def test_node_set():
    html = b"<html><body><p>test</p></body></html>"
    page = Page(html)
    node_1 = page.select("p")[0]
    node_2 = node_1.parent.select("p")[0]
    assert node_1.parent == node_2.parent


class TestPage:
    def test_select(self, stackoverflow_samples):
        page = stackoverflow_samples[0].page
        nodes = page.select(".answer .js-vote-count")
        assert [n.text for n in nodes] == ["20", "16", "0"]

    def test_find_all(self, stackoverflow_samples):
        page = stackoverflow_samples[0].page
        nodes = page.find_all("/users/624900/jterrace")
        assert nodes


def test_equality():
    # we want to make sure that equal html does not result in equality
    same_html = b"<html><body><div><p></p></div></body></html>"
    assert Page(same_html) == Page(same_html)
    assert Page(same_html) is not Page(same_html)


def test_select():
    html = b"<html><body><p></p><p></p></body></html>"
    page = Page(html)
    p_tag_nodes = page.select("p")
    assert len(p_tag_nodes) == 2
    # not used in practice
    # assert len(set(p_tag_nodes)) == 2


def test_tag_name():
    html = b"<html><body><p>bla</p></body></html>"
    p = Page(html)
    tag_node = p.select("p")[0]
    assert tag_node.tag_name == "p"


def test_classes():
    html = b'<html><body><p class="box bordered">bla</p></body></html>'
    p = Page(html)
    tag_node = p.select("p")[0]
    assert tag_node.classes == ("box", "bordered")


def test_find_text_with_whitespace():
    html = b"<html><body><p>    whitespace  \n\t </p></body></html>"
    page = Page(html)
    html_matches = page.find_all("whitespace")

    # should match p, body, html, but not page
    assert len(html_matches) == 3
    assert all(isinstance(hm, HTMLExactTextMatch) for hm in html_matches)


def test_find_text_with_noise():
    html = b"<html><body><p>bla karl bla</p></body></html>"
    page = Page(html)
    assert all(
        not isinstance(html_match, HTMLExactTextMatch)
        for html_match in page.find_all("karl")
    )


def test_get_relative_depth():
    html = b"<html><body><p>bla karl bla</p></body></html>"
    page = Page(html)
    p_tag = page.select("p")[0]
    assert get_relative_depth(p_tag, p_tag) == 0
    assert get_relative_depth(p_tag, p_tag.parent) == 1
    assert get_relative_depth(p_tag, p_tag.parent.parent) == 2
