import logging
import typing
from itertools import combinations, product

from bs4 import BeautifulSoup, Tag
from more_itertools import powerset

PARENT_NODE_COUNT_MAX = 2
CSS_CLASS_COMBINATIONS_MAX = 2

extractor_instance_map = {}
node_instance_map = {}


def get_text_extractor():
    map_key = ("text",)
    if map_key not in extractor_instance_map:
        extractor_instance_map[map_key] = TextValueExtractor()
    return extractor_instance_map[map_key]


def get_attribute_extractor(attr):
    map_key = ("attr", attr)
    if map_key not in extractor_instance_map:
        extractor_instance_map[map_key] = AttributeValueExtractor(attr)
    return extractor_instance_map[map_key]


def get_node_for_soup(soup):
    # use id to avoid __hash__
    soup_key = id(soup)

    if soup_key not in node_instance_map:
        node_instance_map[soup_key] = Node(soup)
    return node_instance_map[soup_key]


class Node:
    soup = None

    def __init__(self, soup):
        self.soup = soup

    def get_root(self):
        root_soup = list(self.soup.parents)[-1]
        return get_node_for_soup(root_soup)

    def get_text(self):
        return self.soup.text

    text = property(get_text)

    def find_all(self, item):
        return list(self._generate_find_all(item))

    def _generate_find_all(self, item):
        assert isinstance(item, str)

        # text
        for soup_node in self.soup.find_all(text=item):
            node = get_node_for_soup(soup_node.parent)
            yield ValueMatch(node, get_text_extractor())

        # attributes
        for soup_node in self.soup.find_all():
            for attr in soup_node.attrs:
                if soup_node[attr] == item:
                    node = get_node_for_soup(soup_node)
                    yield ValueMatch(node, get_attribute_extractor(attr))

        # todo implement other find methods

    def generate_path_selectors(self):
        """
        Generate a selector for the path to the given node.
        :return:
        """
        if not isinstance(self.soup, Tag):
            error_msg = "Only tags can be selected with CSS, %s given" % type(self.soup)
            raise RuntimeError(error_msg)

        # we have a list of n ancestor notes and n-1 nodes including the last node
        # the last node must get selected always

        # so we will:
        # 1) generate all selectors for current node
        # 2) append possible selectors for the n-1 descendants
        # starting with all node selectors and increasing number of used descendants

        # remove unique parents as they don't improve selection
        # body is unique, html is unique, document is bs4 root element
        parents = [
            n for n in self.soup.parents if n.name not in ("body", "html", "[document]")
        ]
        # print(parents)

        # loop from i=0 to i=len(parents) as we consider all parents
        parent_node_count_max = min(len(parents), PARENT_NODE_COUNT_MAX)
        for parent_node_count in range(parent_node_count_max + 1):
            logging.info(
                "generating path selectors with %d parents" % parent_node_count
            )
            # generate paths with exactly parent_node_count nodes
            for parent_nodes_sampled in combinations(parents, parent_node_count):
                path_sampled = (self.soup,) + parent_nodes_sampled
                # logging.info(path_sampled)

                # make a list of selector generators for each node in the path
                # todo limit generated selectors -> huge product
                selector_generators_for_each_path_node = [
                    generate_node_selector(n) for n in path_sampled
                ]

                # generator that outputs selector paths
                # e.g. (div, .wrapper, .main)
                path_sampled_selectors = product(
                    *selector_generators_for_each_path_node
                )

                # create an actual css selector for each selector path
                # e.g. .main > .wrapper > .div
                for path_sampled_selector in path_sampled_selectors:
                    # if paths are not directly connected, i.e. (1)-(2)-3-(4)
                    #  join must be " " and not " > "
                    css_selector = " ".join(reversed(path_sampled_selector))
                    yield css_selector

    def select(self, css_selector):
        return [get_node_for_soup(n) for n in self.soup.select(css_selector)]

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Match:
    """
    Occurrence of a specific sample on a page
    """

    def get_span(self) -> int:
        raise NotImplementedError()

    def get_root(self) -> Node:
        raise NotImplementedError()


class DictMatch(Match):
    match_by_key = None

    def __init__(self, match_by_key: dict):
        self.match_by_key = match_by_key

        soup_nodes = [m.get_root().soup for m in self.match_by_key.values()]
        self.root = get_node_for_soup(_get_root_of_nodes(soup_nodes))

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.match_by_key=}>"

    def get_root(self) -> Node:
        return self.root

    def get_span(self) -> int:
        root = self.get_root()
        return sum(
            [get_relative_depth(m.get_root(), root) for m in self.match_by_key.values()]
        )


class ListMatch(Match):
    matches = None

    def __init__(self, matches: tuple):
        self.matches = matches
        self.root = get_node_for_soup(
            _get_root_of_nodes([m.get_root().soup for m in self.matches])
        )

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.matches=}>"

    def get_root(self) -> Node:
        return self.root

    def get_span(self) -> int:
        return sum(
            [get_relative_depth(m.get_root(), self.get_root()) for m in self.matches]
        )


class ValueMatch(Match):
    node = None
    extractor = None

    def __init__(self, node, extractor):
        self.node = node
        self.extractor = extractor

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.node=}, {self.extractor=}>"

    def get_root(self) -> Node:
        return self.node

    def get_span(self) -> int:
        return 0


class Page(Node):
    """
    One page, i.e. one HTML document.
    """

    def __init__(self, html):
        self.html = html
        soup = BeautifulSoup(self.html, "lxml")
        super().__init__(soup)


class Extractor:
    """
    Class that extracts values from a node.
    """

    def extract(self, node: Node):
        raise NotImplementedError()


class TextValueExtractor(Extractor):
    """
    Class to extract text from a node.
    """

    def extract(self, node: Node):
        return node.soup.text

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class AttributeValueExtractor(Extractor):
    attr = None

    def __init__(self, attr):
        self.attr = attr

    def extract(self, node: Node):
        if self.attr in node.soup.attrs:
            return node.soup[self.attr]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.attr=}>"


class Selector:
    """
    Class to select nodes from another node.
    """

    def select_one(self, node: Node) -> Node:
        raise NotImplementedError()

    def select_all(self, node: Node) -> typing.List[Node]:
        raise NotImplementedError()


class Matcher:
    """
    Class that finds/selects nodes and extracts items from these nodes.
    """

    selector = None
    extractor = None

    def __init__(self, selector: Selector, extractor: Extractor):
        self.selector = selector
        self.extractor = extractor

    def match_one(self, node: Node) -> Match:
        selected_node = self.selector.select_one(node)
        return Match(selected_node, self.extractor)

    def match_all(self, node: Node) -> typing.List[Match]:
        selected_nodes = self.selector.select_all(node)
        return [Match(n, self.extractor) for n in selected_nodes]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.selector=} {self.extractor=}>"


class DictExtractor(Extractor):
    def __init__(self, matcher_by_key: typing.Dict[str, Matcher]):
        self.matcher_by_key = matcher_by_key

    def extract(self, node: Node):
        return {
            key: matcher.match_one(node) for key, matcher in self.matcher_by_key.items()
        }


def generate_node_selector(node):
    """
    Generate a selector for the given node.
    :param node:
    :return:
    """
    assert isinstance(node, Tag)

    # use id
    tag_id = node.attrs.get("id", None)
    if tag_id:
        yield "#" + tag_id

    # use classes
    css_classes = node.attrs.get("class", [])
    for css_class_combo in powerset_max_length(css_classes, CSS_CLASS_COMBINATIONS_MAX):
        css_clases_str = "".join(
            [".{}".format(css_class) for css_class in css_class_combo]
        )
        css_selector = node.name + css_clases_str
        yield css_selector

    # todo: nth applies to whole selectors
    #  -> should thus be a step after actual selector generation
    if isinstance(node.parent, Tag) and hasattr(node, "name"):
        children_tags = [c for c in node.parent.children if isinstance(c, Tag)]
        child_index = list(children_tags).index(node) + 1
        yield ":nth-child(%d)" % child_index

        children_of_same_type = [c for c in children_tags if c.name == node.name]
        child_index = children_of_same_type.index(node) + 1
        yield ":nth-of-type(%d)" % child_index


def powerset_max_length(candidates, length):
    return filter(lambda s: len(s) <= length, powerset(candidates))


def _get_root_of_nodes(nodes):
    # root can be node itself, so it has to be added
    parent_paths_of_nodes = [[node] + list(node.parents) for node in nodes]

    # paths are needed from top to bottom
    parent_paths_rev = [list(reversed(pp)) for pp in parent_paths_of_nodes]
    try:
        ancestor = _get_root_of_paths(parent_paths_rev)
    except RuntimeError:
        raise RuntimeError(f"No common ancestor: {nodes}")
    return ancestor


def _get_root_of_paths(paths):
    """
    Computes the first common ancestor for list of paths.
    :param paths: list of list of nodes from top to bottom
    :return: first common index or RuntimeError
    """
    # go through paths one by one, starting from bottom
    for nodes in reversed(list(zip(*paths))):
        node = nodes[0]
        if all(n is node for n in nodes):
            return nodes[0]

    raise RuntimeError("No common ancestor")


def get_relative_depth(node: Node, root: Node):
    node_parents = list(node.soup.parents)

    # depth of root
    i = node_parents.index(root.soup)

    # depth of element
    j = len(node_parents)

    return j - i
