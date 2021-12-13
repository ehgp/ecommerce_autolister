"""EBAY IMAGE SCRAPER.

Scrapes images from your list on EBAY

Author: ehgp
"""
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path
from bs4 import BeautifulSoup
import re
import string
import json
import pickle
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import Timeoutexception
from selenium.common.exceptions import NoSuchElemention
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random
import pandas as pd
from getpass import getuser
import logging
import logging.config
import sys
import datetime as dt
import yaml
import keyring

# Creds
user = getuser()
ebay_email = keyring.get_password("EBAY_EMAIL", user)
ebay_pass = keyring.get_password("EBAY_PASSWORD", user)

# Paths
path = Path(os.getcwd())
binary_path = Path(path, "chromedriver.exe")
dropship_sh_path = Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx")
dropship_path = Path(path, "Droppping Items")

# Logging
log_config = Path(path, "log_config.yaml")
timestamp = "{:%Y_%m_%d_%H_%M_%S}".format(dt.datetime.now())
with open(log_config, "r") as log_file:
    config_dict = yaml.safe_load(log_file.read())
    # Append date stamp to the file name
    log_filename = config_dict["handlers"]["file"]["filename"]
    base, extension = os.path.splitext(log_filename)
    base2 = "webscraperebay"
    log_filename = "{}{}{}{}".format(base, base2, timestamp, extension)
    config_dict["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)

PAGES = 3

DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.202 Safari/537.36",
    "origin": "https://www.facebook.com",
}


EBAY_LOGIN = "https://www.ebay.com/signin/"

EBAY_USERNAME_XPATH = "//input[@name='email']"

EBAY_PASSWORD_XPATH = "//input[@name='password']"

EBAY_LOGIN_BUTTON_XPATH = "//button[@type='submit']"

EBAY_SOUP_LINK_FINDALL_EXT = '"a", attrs={"class": "display-inline-block listing-link"}'

EBAY_SOUP_TITLE_EXT = "h1.it-ttl"

EBAY_SOUP_DES_EXT = 'id="desc_ifr"'

EBAY_SOUP_PRICE_EXT = '"span", attrs={"itemprop": "price"}'

EBAY_SOUP_SHIPPRICE_EXT = '"span", attrs={"id": "fshippingCost"}'

EBAY_SOUP_SHIPHOW_EXT = '"span", attrs={"itemprop": "availableAtOrFrom"}'

EBAY_LINK_LIST = (
    "https://www.ebay.com/mye/myebay/watchlist?custom_list_id=WATCH_LIST&page_number="
)

EBAY_SOUP_IMAGELINK_96_EXT = r"(http:|https:)(\/\/i.ebayimg.com[^\"\']*)(96.png|96.jpg|96.jpeg|96.gif|96.png|96.svg|96.webp)"

EBAY_SOUP_IMAGELINK_300_EXT = r"(http:|https:)(\/\/i.ebayimg.com[^\"\']*)(300.png|300.jpg|300.jpeg|300.gif|300.png|300.svg|300.webp)"

EBAY_SOUP_IMAGELINK_64_EXT = r"(http:|https:)(\/\/i.ebayimg.com[^\"\']*)(64.png|64.jpg|64.jpeg|64.gif|64.png|64.svg|64.webp)"

# Configure ChromeOptions
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-EBAY")
# options.add_argument('--proxy-server=https://'+ self.proxies[0])
# options.add_argument('--proxy-server=http://'+ self.proxies[0])
# options.add_argument('--proxy-server=socks5://'+ self.proxies[0])
options.add_argument("--disable-notifications")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors")
# options.add_argument('user-agent = Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')
# options.add_argument('--headless')
# options.add_argument('--window-size=1910x1080')
# options.add_argument('--proxy-server=http://'+ proxies[0]))


def save_to_file_wishlist(response, i):
    """Save response to response.html."""
    with open(
        Path(path, "ebay responses", f"responseebaywishlist{i}.html"),
        "w",
        encoding="utf-8",
    ) as fp:
        fp.write(response)


def save_html_to_file(response, title):
    """Save response to response.html."""
    with open(
        Path(path, "ebay responses", f"responseebay{title}.html"),
        "w",
        encoding="utf-8",
    ) as fp:
        fp.write(response)


def fix_cookies_and_load_to_requests(cookie_list, request_session):
    """Fix cookie values and add cookies to request_session."""
    for index in range(len(cookie_list)):
        for item in cookie_list[index]:
            if type(cookie_list[index][item]) != str:
                cookie_list[index][item] = str(cookie_list[index][item])
        cookies = requests.utils.cookiejar_from_dict(cookie_list[index])
        request_session.cookies.update(cookies)
    return request_session


new_titles = []
new_descriptions = []
new_prices = []
new_ship_prices = []
new_ship_how = []
extracted_links = []


def listingscraper(new_items):
    """Scrape listing title, description, price, ship price."""
    for idx, link in enumerate(new_items):

        page = requests.get(link)

        save_html_to_file(page.text, idx)

        soup = BeautifulSoup(page.text, "lxml")
        # json_content = soup.find_all(type="application/ld+json")
        # content = json.loads(json_content[0].contents[0])

        for link in soup.findAll(EBAY_SOUP_LINK_FINDALL_EXT):
            extracted_links.append(link.get("href").split("ref")[0])
        try:
            title = (
                (soup.select(EBAY_SOUP_TITLE_EXT)[0].text.strip())
                .replace("Details about  \xa0", "")
                .replace("from China", "")
                .replace("Worldwide", "")
                .replace("Etsy", "")
                .replace("etsy", "")
                .replace("ETSY", "")
                .replace("eBay", "")
                .replace("ebay", "")
                .replace("EBAY", "")
                .replace("AliExpress", "")
                .replace("aliexpress", "")
                .replace("ALIEXPRESS", "")
                .replace("LIFETIME WARRANTY", "")
                .replace("WARRANTY", "")
                .replace("lifetime warranty", "")
                .replace("|", "")
                .replace("\n", " ")
                .replace("\xa0", "")
                .replace(" Store Categories Store Categories ", "")
                .replace("US $", "")
                .replace("Return", "")
                .replace("return", "")
                .replace("Refund", "")
                .replace("refund", "")
            )

        except Exception as e:
            print(e)
            pass

        new_titles.append(title)

        try:
            description_soup = soup.find(EBAY_SOUP_DES_EXT)["src"]
            description = (
                BeautifulSoup((requests.get(description_soup).content), "lxml")
                .get_text(strip=True, separator="\n")
                .replace("Details about  \xa0", "")
                .replace("from China", "")
                .replace("Worldwide", "")
                .replace("Etsy", "")
                .replace("etsy", "")
                .replace("ETSY", "")
                .replace("eBay", "")
                .replace("ebay", "")
                .replace("EBAY", "")
                .replace("AliExpress", "")
                .replace("aliexpress", "")
                .replace("ALIEXPRESS", "")
                .replace("LIFETIME WARRANTY", "")
                .replace("WARRANTY", "")
                .replace("lifetime warranty", "")
                .replace("|", "")
                .replace("\n", " ")
                .replace("\xa0", "")
                .replace(" Store Categories Store Categories ", "")
                .replace("US $", "")
                .replace("Return", "")
                .replace("return", "")
                .replace("Refund", "")
                .replace("refund", "")
            )
        # product-description > div > div.detailmodule_html > div > div > div > div > div > div > div > div > div:nth-child(4) > div
        except Exception as e:
            print(e)
            pass

        new_descriptions.append(description)

        try:
            price = (
                soup.findAll(EBAY_SOUP_PRICE_EXT)[0]
                .text.replace("Details about  \xa0", "")
                .replace("from China", "")
                .replace("Worldwide", "")
                .replace("Etsy", "")
                .replace("etsy", "")
                .replace("ETSY", "")
                .replace("eBay", "")
                .replace("ebay", "")
                .replace("EBAY", "")
                .replace("AliExpress", "")
                .replace("aliexpress", "")
                .replace("ALIEXPRESS", "")
                .replace("LIFETIME WARRANTY", "")
                .replace("WARRANTY", "")
                .replace("lifetime warranty", "")
                .replace("|", "")
                .replace("\n", " ")
                .replace("\xa0", "")
                .replace(" Store Categories Store Categories ", "")
                .replace("US $", "")
                .replace("Return", "")
                .replace("return", "")
                .replace("Refund", "")
                .replace("refund", "")
            )

        except Exception as e:
            print(e)
            pass

        new_prices.append(price)

        try:
            ship_price = (
                str(soup.findAll(EBAY_SOUP_SHIPPRICE_EXT)[0].text)
                .replace("Details about  \xa0", "")
                .replace("from China", "")
                .replace("Worldwide", "")
                .replace("Etsy", "")
                .replace("etsy", "")
                .replace("ETSY", "")
                .replace("eBay", "")
                .replace("ebay", "")
                .replace("EBAY", "")
                .replace("AliExpress", "")
                .replace("aliexpress", "")
                .replace("ALIEXPRESS", "")
                .replace("LIFETIME WARRANTY", "")
                .replace("WARRANTY", "")
                .replace("lifetime warranty", "")
                .replace("|", "")
                .replace("\n", " ")
                .replace("\xa0", "")
                .replace(" Store Categories Store Categories ", "")
                .replace("US $", "")
                .replace("Return", "")
                .replace("return", "")
                .replace("Refund", "")
                .replace("refund", "")
            )
        except Exception as e:
            print(e)
            pass

        new_ship_prices.append(ship_price)

        try:
            ship_how = str(soup.findAll(EBAY_SOUP_SHIPHOW_EXT)[0].text)
        except Exception as e:
            print(e)
            ship_how = ""
            pass

        new_ship_how.append(ship_how)

    new_items = pd.DataFrame(
        {
            "new_title": new_titles,
            "new_description": new_descriptions,
            "new_link": new_items,
            "new_price": new_prices,
            "new_ship_price": new_ship_prices,
            "new_ship_how": new_ship_how,
        }
    )

    new_items.to_csv(Path(path, "Dropshipping Items", "new_items_ebay.csv"))


# title = '2020 Hot Wheels 2016 Bugatti Chiron Black #89/250 Factory Fresh'
# page = requests.get('https://www.ebay.com/itm/US-Mini-Portable-Fast-Heater-Heated-Heating-Electric-Hot-Air-Fan-Space-Desk-400W/193752419857?')
# soup = BeautifulSoup(page.text, 'lxml')
# save_html_to_file(page.text,title)
# <script type="application/ld+json">


def linkscraperebay():
    """Extract Links from EBAY list."""
    # Go to the website
    with webdriver.Chrome(executable_path=binary_path, options=options) as driver:
        driver.get(EBAY_LOGIN)
        time.sleep(random.randint(10, 15))
        if os.path.exists(".profile-EBAY") is False:
            # Logging IN
            time.sleep(random.uniform(0.15, 0.4))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_USERNAME_XPATH)))
                .send_keys(ebay_email)
            )
            username = username
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_PASSWORD_XPATH)))
                .send_keys(ebay_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_LOGIN_BUTTON_XPATH)))
                .click()
            )
            login = login
            time.sleep(random.randint(60, 120))
        for x in range(1, PAGES):
            driver.get(f"{EBAY_LINK_LIST}{x}")
            time.sleep(random.randint(10, 15))
            elem = driver.find_element_by_xpath("//*")
            source_code = elem.get_attribute("outerHTML")
            save_to_file_wishlist(source_code, x)

            soup = BeautifulSoup(source_code, "lxml")

            for link in soup.findAll("a", attrs={"class": "title"}):
                extracted_links.append(link.get("href") + "?")

    product_list = pd.read_excel(
        Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx"),
        sheet_name="PRODUCT_LIST",
    )
    not_new_items = list(product_list["Link"])

    new_items = [link for link in extracted_links if link not in not_new_items]

    listingscraper(new_items)


def imagewebscraperebay(URL, title):
    """Webscrape Images from EBAY."""
    page = requests.get(URL)

    save_html_to_file(page.text, title)

    soup = BeautifulSoup(page.text, "lxml")

    if (
        re.findall(
            EBAY_SOUP_IMAGELINK_96_EXT,
            str(soup),
        )
        == []
    ):
        imgfilename = re.findall(
            EBAY_SOUP_IMAGELINK_300_EXT,
            str(soup),
        )

    elif (
        re.findall(
            EBAY_SOUP_IMAGELINK_300_EXT,
            str(soup),
        )
        == []
    ):
        imgfilename = re.findall(
            EBAY_SOUP_IMAGELINK_64_EXT,
            str(soup),
        )

    else:
        imgfilename = re.findall(
            EBAY_SOUP_IMAGELINK_96_EXT,
            str(soup),
        )

    imgfilename = ["".join(i) for i in imgfilename]
    imgfilename = list(dict.fromkeys(imgfilename))

    os.makedirs(Path(path, "Dropshipping Items", title), exist_ok=True)

    for idx, url in enumerate(imgfilename):
        with open(
            Path(path, "Dropshipping Items", title, f"{title}{idx}.jpg"), "wb"
        ) as f:
            response = requests.get(url.replace("96", "300"))
            f.write(response.content)
