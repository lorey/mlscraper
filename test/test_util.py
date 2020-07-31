from bs4 import BeautifulSoup
from pytest import fixture

from autoscrape.util import generate_path_selectors, generate_unique_path_selectors


@fixture
def basic_soup():
    html = b"""<html><body>
        <div class="wrapper box"><div>Rose are red, the ocean is blue, this div will get selected, too.</div></div>
        <div class="main article">
        <div class="test wrapper box">
            <div id="sample">bla</div>
        </div>
        </div>
        </body></html>"""
    soup = BeautifulSoup(html, "lxml")
    return soup


def test_generate_path_selectors(basic_soup):
    node = basic_soup.select("#sample")[0]
    selectors = generate_path_selectors(node)

    # test that output contains specific selectors
    # assert '#sample' in selectors
    assert "div.wrapper > div" in selectors

    for css_sel in selectors:
        assert basic_soup.select(css_sel)


def test_generate_unique_path_selectors(basic_soup):
    node = basic_soup.select("#sample")[0]
    selectors = list(generate_unique_path_selectors(node))

    # there are unique selectors
    assert len(selectors) > 0

    # all selectors must match exactly once (uniqueness)
    assert all(len(basic_soup.select(css_sel)) == 1 for css_sel in selectors)

    assert ".wrapper.box > div" not in selectors
    assert "div > div" not in selectors
    # assert "#sample" in selectors
