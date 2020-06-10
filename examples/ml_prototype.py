# this is just a prototype for classifier-based element detection
# - using actual machine learning, not heuristics
# - detecting elements defined by icons, e.g. a dollar icon follow by a price
import codecs
import logging
import re
from random import sample

import pandas as pd
import requests
from bs4 import BeautifulSoup, NavigableString
from sklearn import tree
from sklearn.base import TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier


class Preprocessing(TransformerMixin):
    def __init__(self, element):
        self.element = element

    def fit(self, X, y):
        # todo define classes to extract here, doing it in transform will cause bugs
        return self

    def transform(self, X, y=None, **fit_params):
        df = pd.DataFrame({"node": X})
        df["has_content"] = df["node"].apply(
            lambda n: type(n) is NavigableString and len(str(n).strip()) > 0
        )
        df["is_same_type"] = df["node"].apply(lambda n: type(n) == type(self.element))
        sibling_prev = self.element.previous_sibling
        sibling_prev_classes = sibling_prev.attrs.get("class")

        df["prev_sibling"] = df["node"].apply(lambda n: n.previous_sibling)

        for css_class in sibling_prev_classes:
            df["sibling_prev_has_class_{}".format(css_class)] = df[
                "prev_sibling"
            ].apply(
                lambda n: css_class in n.attrs.get("class", [])
                if hasattr(n, "attrs")
                else False
            )

        features = [c for c in df.columns if c.startswith("sibling")] + ["is_same_type"]
        return df[features]


def main():
    # obfuscated the url a little :)
    url_rot = "uggcf://jjj.fgnegonfr.qr/betnavmngvba/jrygraznpure-tzou/"
    url = codecs.decode(url_rot, "rot_13")

    resp = requests.get(url)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "lxml")

    print("Found {} nodes".format(len(list(soup.descendants))))

    # find the element to crawl on the site
    elements_in_site = soup.find_all(text=re.compile(r"\s*2017\s*"))
    element = elements_in_site[0]  # type: NavigableString

    print("ELEMENT")
    print(element)

    pipeline = Pipeline(
        [
            ("preprocessing", Preprocessing(element)),
            # ("clf", SVC(class_weight="balanced", probability=True)),
            ("clf", DecisionTreeClassifier(class_weight="balanced")),
        ]
    )

    # under-sample negative and over-sample positive samples
    sample_count = 1000
    oversampling_factor = 10

    samples = sample(list(soup.descendants), sample_count)
    X = samples + [element] * oversampling_factor
    y = [n == element for n in samples] + [True] * oversampling_factor

    # train the pipeline
    pipeline = pipeline.fit(X, y)

    # print the tree if it's a decision tree
    # -> select last pipeline step
    if type(pipeline.steps[-1][1]) is DecisionTreeClassifier:
        print("TREE")
        clf_tree = pipeline.steps[1][1]
        print(tree.export_text(clf_tree))

    # perform sanity check: element we're looking for should get matched
    is_element_matched = pipeline.predict([element])[0]
    print("Element is {}".format(is_element_matched))
    if not is_element_matched:
        logging.warning("Element is not matched, classifier is probably broken")

    # print out samples for debugging
    for x, y_ in zip(X, y):
        is_match = pipeline.predict([x])[0]
        if is_match:
            print(x)
            print("Class: " + str(y_))
            print("Prediction: " + str(is_match))
            print("Proba: " + str(pipeline.predict_proba([x])))
            print()


if __name__ == "__main__":
    main()
