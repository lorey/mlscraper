from mlscraper.samples import Sample
from mlscraper.selectors import generate_selector_for_nodes
from mlscraper.selectors import make_matcher_for_samples
from mlscraper.util import Page


def test_make_matcher_for_samples():
    page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
    page1 = Page(page1_html)
    sample1 = Sample(page1, "test")

    page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
    page2 = Page(page2_html)
    sample2 = Sample(page2, "hallo")

    samples = [sample1, sample2]
    assert make_matcher_for_samples(samples).selector.css_rule in ["p.test", ".test"]


def test_generate_selector_for_nodes():
    page1_html = '<html><body><p class="test">test</p><p>bla</p></body></html>'
    page1 = Page(page1_html)
    sample1 = Sample(page1, "test")

    page2_html = '<html><body><div></div><p class="test">hallo</p></body></html>'
    page2 = Page(page2_html)
    sample2 = Sample(page2, "hallo")

    samples = [sample1, sample2]

    nodes = [s.get_matches()[0].get_root() for s in samples]
    gen = generate_selector_for_nodes(nodes, None)
    # todo .test is also possible
    assert ["p.test"] == [sel.css_rule for sel in gen]
