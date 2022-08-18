import logging

import requests
from mlscraper.html import Page
from mlscraper.samples import Sample, TrainingSet
from mlscraper.training import train_scraper


def main():
    """
    This example shows you how to build a scraper for shoes in the pro direct tennis website
    """

    # fetch the page to train
    einstein_url = "https://www.prodirecttennis.com/search.aspx?q=nike+shoes&o=lth"
    headers = {
  'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.5',
  'Accept-Encoding': 'gzip, deflate, br',
  'Referer': 'https://www.prodirecttennis.com/search.aspx?q=nike+shoes&o=htl',
  'DNT': '1',
  'Connection': 'keep-alive',
  'Cookie': 'ASP.NET_SessionId=hxowndcmstqsbtqxvsjqutff; IsLoggedIn=False; HasItemsInBasket=False; Currency=GBP; _abck=5BB3F96F12E76CB6058F6AEBBF424562~0~YAAQzRY2F78OW66CAQAA9UK4sAhnt9Qok957XXDEgMoCGuNnUGIuHUEb85bESgcU5LY9nCQO2xviBKi4QG4df+kz3KS3alGo+D22vLSDW/kj+XHb5tmj/LKuCqel3KFT5tyhtp3hPNyUI9roEmhLwyUKHs3Qr1NTYMHxXAokZW7M12CsjXAgg3grajhqDhW+sbUe4ovJlFZOpzYwkWkW5/bVMBNbKZEELVrFVRQgd5UK43P9aKGaPhjuR/GoOw/fsNAYvbmWVFPtvl4g0+TVwAFLWKPyCgVlNgcvywpDVJldyl9IHCtPM34l1iI2FQ1Lfqj1+AjfLrfgYF3dmyWblYmJgBg1aahLEXoFRHhUUi1ozF6+ZTyOUxFY54n47QfegmgdJlr+XrSbqOy/K0hSWt2GYHpyDx+uh8eX1Bae~-1~-1~-1; ak_bmsc=C0E08958A3F86B88016B6678EDC64519~000000000000000000000000000000~YAAQzRY2F1YiW66CAQAAZnK+sBBPkD7loTrGsH81ehL1a+V+jcHr+wKWdseToumvxDbJKMxjhXvL+40PxOcbzKsjJajIz3b8QIo0wMFC85/cmxaUdHY9SeF3XEqyr0OAJBkCZK/xr2R8RAOx+9S5mb5goHrUrawnXsderzBHzBuXiecu+Wt7EEE/ya/dgfcSPt5IjP866XYTPEjqLokiW5rn6tDcpBJDEnUsLW77lFh2dKcqlbVYNCxNabsqFS5MkilhPGFi9RIiLWWgOg+O3BENy4kx1lF052UY8b3uByJLF/LfkX6pu1melLxn95nHNIDQ9Yv6hnKHFQR40qtMBcNkBX0qjsrvdT2xjja3mKN8My8V86ycKua+15Rj5W94MQE9MwkTjNAkNvrsGQGvw7ZphdHW5WB3sXmL1VKeiCvGCOZt+vioBykxbPCR0KpWuhPWqH2H1kj8; bm_sz=05D5574700055AF18C0D585B76419F8B~YAAQzRY2F5gDW66CAQAALhqzsBATzXRjNOjMQJcKNfKdzlUZxwfB1QNhWi1fh1KKIdTJI7L6yTDQxt/0WOwn3b9fMheRvFnixE9FDe1LGYL6nvqkcy6wZn6EuNzpVU14qwmFTEN8pkW+3VhmTkIswehJmV7/XIfyS5ugw97ploLKJ5StwmODQ+xt4zaryU2oA6TkuMsHUc1ZurEcoEk3jU1Gxt0/iW8H2F+uLwZdv8+Njn39/FUsBlQigippkx4enye7yjncy0icEXOKMNNxK48oIoNeT75Fs6NfwMX3JxeXcG+DbCYqzVPd1b8=~4272193~3223617; MobileViewChoice=grid; _screenSize=large; bm_mi=4FEE586E7243562452B9F11A9393B618~YAAQzRY2F6oOW66CAQAAGj24sBBsePrS50bt7hWOzvM4oeKu+B3d0540dkcPpv8yooFD+nJqqhtdk3Ld34ajn3VBLejrF/Vjn99ZclDMy7g5YZK9kUALE66f1+jII5ejBA7rHw0oyHEkpablovnSh1+NYVxOqU1TzrQMnwJorZ81aEf/V0V9lBrvYrTfMcdCtvulU/zn91OlKfrzWVJOtx7+STKfX9iD1J2Lw6o6Fb4RJoF5SbQIayu6OS/Yi3gSoa8gL+gr4yrB7XZK/4wIjimhROCsh1ocIG+ICwkGTZDBquYlWxMT7OHBtLJmnN3m3MnJefP4BmbAaXhl7e8gRw==~1; bm_sv=C1FA96184B6C10BA121307B7B3B9880F~YAAQzRY2F8WZXK6CAQAANLjxsBB6ipiCZFO8rZVUYa1NIqmZqiIMMOEs0+2nSpi3Ypow9oTdAlTSPCotRLdJL/PyWwVM4mucskTyEzHwUBdXtSCTPeYth8ylTtfOAnTBRbqueiPA0rx22G+9PrAjpE3SsqkcW5twqswdMSFRc9wMTVJgGfgQrQQ5DNPJKjAXm1H3JbtyUKIMn5GoBSx+W788KU+FjpR1Ggai4UXxX+W4zoioELHg6ivypkwCMaQSqO4Ij50NYGierw==~1',
  'Upgrade-Insecure-Requests': '1',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-User': '?1'
}
    resp = requests.get(einstein_url,headers=headers,timeout=10)
    assert resp.status_code == 200

    # The first page shows 24 shoes, so we need 24 samples
    training_set = TrainingSet()
    page = Page(resp.content)
    list_sample_labels = [
        # First column
        {
            "name": "Nike Cushion No Show Trainer Socks 3 Pack",
            "price": "£10.00",
        },
        {
            "name": "Nike Womens Benassi JDI Slides",
            "price": "£22.00",
        },
        {
            "name": "Nike Womens Sportswear Victori One Shower Slide",
            "price": "£23.00",
        },
        {
            "name": "Nike Victori One Shower Slide",
            "price": "£23.00",
        },
        
        
        ]

    #]
    for sample_label in list_sample_labels:
        sample = Sample(page, sample_label)
        training_set.add_sample(sample)

    print("Training set created")

    # train the scraper with the created training set
    scraper = train_scraper(training_set)
    
    print("Get results")
    # scrape another page
    resp = requests.get(
        "https://www.prodirecttennis.com/search.aspx?q=nike+shoes&o=htl",
        headers=headers,
        timeout=10,
        )
    result = scraper.get(Page(resp.content))
    print(result)
    # returns {'name': 'J.K. Rowling', 'born': 'July 31, 1965'}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
