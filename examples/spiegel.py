
"""
To use this:
pip install requests
pip install --pre mlscraper
To automatically build any scraper, check out https://github.com/lorey/mlscraper
"""

import logging

import requests

from mlscraper.html import Page
from mlscraper.samples import Sample, TrainingSet
from mlscraper.training import train_scraper

ARTICLES = ({
    'url': 'https://www.spiegel.de/politik/kristina-haenel-nach-abstimmung-ueber-219a-im-bundestag-dieser-kampf-ist-vorbei-a-f3c04fb2-8126-4831-bc32-ac6c58e1e520',
    'title': '»Dieser Kampf ist vorbei«',
    "subtitle": "Ärztin Kristina Hänel über die Abstimmung",
    "teaser": "Der umstrittene Paragraf zum »Werbeverbot« für Abtreibung ist seit heute Geschichte – und die Gießenerin Kristina Hänel, die seit Jahren dafür gekämpft hat, kann aufatmen. Wie geht es für die Medizinerin jetzt weiter?",
    "authors": ["Nike Laurenz"],
    "published": "24.06.2022, 14.26 Uhr",
},
    {
        'url': 'https://www.spiegel.de/politik/deutschland/abtreibung-abschaffung-von-paragraf-219a-fuer-die-muendige-frau-kommentar-a-784cd403-f279-4124-a216-e320042d1719',
        'title': 'Für die mündige Frau',
        'subtitle': 'Abschaffung von Paragraf 219a',
        'teaser': 'Die Ampelkoalition hat das sogenannte Werbeverbot für Schwangerschaftsabbrüche abgeschafft. Eine gute Entscheidung – aber die Diskussion über das Abtreibungsrecht muss weitergehen.',
        'authors': ['Anke Dürr'],
        'published': '24.06.2022, 12.52 Uhr',
    },
    {
        'url': 'https://www.spiegel.de/wirtschaft/soziales/inflation-was-die-teuerung-fuer-hartz-iv-empfaenger-bedeutet-a-7d4b6a94-dac5-41bd-bff7-b623854b3474',
        'title': 'Was die Inflation für Hartz-IV-Empfänger bedeutet',
        'subtitle': 'Einkaufen vor einem Jahr und heute',
        'teaser': 'Silvana van Baaren hat einen Kassenzettel aus dem Sommer 2021 aufbewahrt und kauft nun genau die gleichen Produkte noch einmal. Das Ergebnis ihres Inflationsexperiments überrascht.',
        'authors': ['Thies Schnack', 'Jonathan Miske'],
        'published': '04.07.2022, 20.18 Uhr',
    }
)


def train_and_scrape():
    """
    This trains the scraper and scrapes two other pages.
    """
    scraper = train_spon_scraper()

    urls_to_scrape = [
        'https://www.spiegel.de/politik/deutschland/bundesverteidigungsministerin-christine-lambrecht-will-keine-transportpanzer-in-die-ukraine-liefern-a-31aa309f-09ed-46d6-aeb0-c46c988a96d1',
        'https://www.spiegel.de/wirtschaft/service/energiesparmassnahme-vonovia-will-nachts-die-heizungen-herunterdrehen-a-85367049-2b73-4f2d-bac8-d2017c3f7b87',
    ]
    for url in urls_to_scrape:
        # fetch page
        article_resp = requests.get(url)
        article_resp.raise_for_status()
        page = Page(article_resp.content)

        # extract result
        result = scraper.get(page)
        print(result)


def train_spon_scraper():
    training_set = make_training_set_for_articles(ARTICLES)
    scraper = train_scraper(training_set, complexity=2)
    return scraper


def make_training_set_for_articles(articles):
    """
    This creates a training set to automatically derive selectors based on the given samples.
    """
    keys_to_train = ['title', 'subtitle', 'teaser', 'authors', 'published']
    training_set = TrainingSet()
    for article in articles:
        # fetch page
        article_url = article['url']
        html_raw = requests.get(article_url).content
        page = Page(html_raw)

        # create and add sample
        article_data = {k: v for k, v in article.items() if k in keys_to_train}
        sample = Sample(page, article_data)
        training_set.add_sample(sample)

    return training_set


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    train_and_scrape()
