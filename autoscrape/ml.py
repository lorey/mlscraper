from sklearn.base import TransformerMixin
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer
from sklearn.tree import DecisionTreeClassifier
from sklearn_pandas import DataFrameMapper


class NodePreprocessing(TransformerMixin):
    """Preprocesses a list of nodes."""

    def fit(self, X, y):
        return self

    def transform(self, X, y=None, **fit_params):
        # create basic df
        df = pd.DataFrame(X, columns=["node"])

        df["node_type"] = df["node"].apply(lambda n: str(type(n)))
        df["node_classes"] = df["node"].apply(extract_classes)

        df["parent_classes"] = df["node"].apply(lambda n: extract_classes(n.parent))

        return df


def train_pipeline(nodes, targets):
    assert len(nodes) == len(targets), "len(nodes) != len(targets)"

    dfm_features = [
        (["node_type"], OneHotEncoder()),
        ("node_classes", MultiLabelBinarizer()),
        ("parent_classes", MultiLabelBinarizer()),
    ]
    dfm = DataFrameMapper(dfm_features)

    pipeline_steps = [
        ("pre", NodePreprocessing()),
        ("pd", dfm),
        ("classifier", DecisionTreeClassifier(class_weight="balanced")),
    ]
    pipeline = Pipeline(steps=pipeline_steps)

    pipeline.fit(nodes, targets)

    return pipeline


def extract_classes(n):
    return n.attrs.get("class", []) if hasattr(n, "attrs") else []
