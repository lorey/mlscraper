import pandas as pd
from sklearn.base import TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from autoscraper.util import generate_unique_path_selectors


class NodePreprocessing(TransformerMixin):
    """Preprocesses a list of nodes."""

    def __init__(self):
        self.css_selectors = None

    def fit(self, X, y):
        # get all css selectors
        css_selectors = set()
        for node, is_target in zip(X, y):
            if is_target:
                # todo doesn't work for multi-result pages
                #  because a unique selector cannot select multiple elements on one page

                css_selectors |= set(generate_unique_path_selectors(node))
        self.css_selectors = css_selectors

        return self

    def transform(self, X, y=None, **fit_params):
        # create basic df
        df = pd.DataFrame(X, columns=["node"])

        def is_selector_match(selector, node):
            root = list(node.parents)[0]
            return node in root.select(selector)

        for css_selector in self.css_selectors:
            col = "select: %s" % css_selector
            df[col] = df["node"].apply(lambda n: is_selector_match(css_selector, n))

        return df[[c for c in df.columns if c not in ["node"]]]


def train_pipeline(nodes, targets):
    assert len(nodes) == len(targets), "len(nodes) != len(targets)"

    pipeline_steps = [
        ("pre", NodePreprocessing()),
        ("classifier", DecisionTreeClassifier(class_weight="balanced")),
    ]
    pipeline = Pipeline(steps=pipeline_steps)

    pipeline.fit(nodes, targets)

    return pipeline


def extract_classes(n):
    return n.attrs.get("class", []) if hasattr(n, "attrs") else []
