"""ETSY IMAGE SCRAPER.

Scrapes images from your list on ETSY

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
etsy_email = keyring.get_password("ETSY_EMAIL", user)
etsy_pass = keyring.get_password("ETSY_PASSWORD", user)

# Paths
path = Path(os.getcwd())
binary_path = Path(path, "chromedriver.exe")
dropship_sh_path = Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx")
dropship_path = Path(path, "Droppping Items")

# Logging
Path("log").mkdir(parents=True, exist_ok=True)
log_config = Path(path, "log_config.yaml")
timestamp = "{:%Y_%m_%d_%H_%M_%S}".format(dt.datetime.now())
with open(log_config, "r") as log_file:
    config_dict = yaml.safe_load(log_file.read())
    # Append date stamp to the file name
    log_filename = config_dict["handlers"]["file"]["filename"]
    base, extension = os.path.splitext(log_filename)
    base2 = "webscraperetsy"
    log_filename = "{}{}{}{}".format(base, base2, timestamp, extension)
    config_dict["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)

PAGES = 5

DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.202 Safari/537.36",
    "origin": "https://www.facebook.com",
}

ETSY_LOGIN = "https://www.etsy.com/signin"

ETSY_USERNAME_XPATH = "//input[@name='email']"

ETSY_PASSWORD_XPATH = "//input[@name='password']"

ETSY_LOGIN_BUTTON_XPATH = "//button[@type='submit']"

ETSY_SOUP_SHIPPRICE_EXT = (
    '"p", attrs={"class": "wt-text-body-03 wt-mt-xs-1 wt-line-height-tight"},'
)

ETSY_SOUP_SHIPHOW_EXT = (
    '"div", attrs={"class": "wt-grid__item-xs-12 wt-text-black wt-text-caption"},'
)

ETSY_LINK_LIST = (
    "https://www.etsy.com/people/erickhgarciap?ref=hdr_user_menu-profile&page="
)

ETSY_SOUP_IMAGELINK_EXT = (
    r"(http:|https:)(\/\/[^\"\']*\.(?:png|jpg|jpeg|gif|png|svg|webp))"
)

# Configure ChromeOptions
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-ETSY")
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
        Path(path, "etsy responses", f"responseetsywishlist{i}.html"),
        "w",
        encoding="utf-8",
    ) as fp:
        fp.write(response)


def save_html_to_file(response, title):
    """Save response to response.html."""
    with open(
        Path(path, "etsy responses", f"responseetsy{title}.html"),
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


# you function to get the cookies from the file.
def load_cookies(filename):
    """Load cookies from file."""
    with open(filename, "rb") as f:
        return pickle.load(f)


new_descriptions = []
new_titles = []
extracted_links = []
new_prices = []
new_ship_prices = []
new_ship_how = []


def listingscraper(new_items):
    """Scrape listing title, description, price, ship price."""
    for idx, link in enumerate(new_items):

        page = requests.get(link)

        save_html_to_file(page.text, idx)

        soup = BeautifulSoup(page.text, "lxml")
        json_content = soup.find_all(type="application/ld+json")
        content = json.loads(json_content[0].contents[0])
        try:
            title = (
                content["name"]
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
            title = ""
            pass

        new_titles.append(title)

        try:
            description = (
                content["description"]
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
            description = ""
            pass

        new_descriptions.append(description)

        try:
            price = (
                content["offers"]["highPrice"]
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
            price = ""
            pass

        new_prices.append(price)

        try:
            ship_price = (
                str(soup.find(ETSY_SOUP_SHIPPRICE_EXT).text)
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
            ship_price = ""
            pass

        new_ship_prices.append(ship_price)

        try:
            ship_how = str(soup.find(ETSY_SOUP_SHIPHOW_EXT).text)
        except Exception as e:
            print(e)
            ship_how = ""
            pass

        new_ship_how.append(ship_how)

    new_items_df = pd.DataFrame(
        {
            "new_title": new_titles,
            "new_description": new_descriptions,
            "new_link": new_items,
            "new_price": new_prices,
            "new_ship_price": new_ship_prices,
            "new_ship_how": new_ship_how,
        }
    )

    new_items_df.to_csv(Path(path, "Dropshipping Items", "new_items_etsy.csv"))


# title = 'Skateboard Complete Standard Street Cruiser 32 INCH BY 8 INCH Board'
# page = requests.get('https://www.etsy.com/listing/869334327/skateboard-complete-standard-street?')
# soup = BeautifulSoup(page.text, 'lxml')
# save_html_to_file(page,0)
# <script type="application/ld+json">


def linkscraperetsy():
    """Extract Links from ETSY list."""
    # Go to the website
    with webdriver.Chrome(executable_path=binary_path, options=options) as driver:
        driver.get(ETSY_LOGIN)
        if os.path.exists(".profile-ETSY") is False:
            # Logging IN
            time.sleep(random.uniform(0.15, 0.4))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_USERNAME_XPATH)))
                .send_keys(etsy_email)
            )
            username = username
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_PASSWORD_XPATH)))
                .send_keys(etsy_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_LOGIN_BUTTON_XPATH)))
                .click()
            )
            login = login
        # Save the cookies in a file
        with open(Path(path, "cookiesetsy.dat"), "wb") as f:
            pickle.dump(driver.get_cookies(), f)

    saved_cookies_list = load_cookies(str(path) + "cookiesetsy.dat")

    # Set request session
    initial_state = requests.Session()

    initial_state_with_cookies = fix_cookies_and_load_to_requests(
        cookie_list=saved_cookies_list, request_session=initial_state
    )

    for x in range(1, PAGES):
        time.sleep(random.uniform(0.15, 1.1))
        page = initial_state_with_cookies.get(f"{ETSY_LINK_LIST}{x}#")

        save_to_file_wishlist(page.text, x)

        soup = BeautifulSoup(page.text, "lxml")

        for link in soup.findAll(
            "a", attrs={"class": "display-inline-block listing-link"}
        ):
            extracted_links.append(link.get("href").split("ref")[0])

    product_list = pd.read_excel(
        Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx"),
        sheet_name="PRODUCT_LIST",
    )
    not_new_items = list(product_list["Link"])

    new_items = [link for link in extracted_links if link not in not_new_items]

    listingscraper(new_items)


def imagewebscraperetsy(URL, title):
    """Webscrape Images from ETSY."""
    page = requests.get(URL)

    save_html_to_file(page.text, title)

    soup = BeautifulSoup(page.text, "lxml")
    soup = soup

    imgfilename = re.findall(ETSY_SOUP_IMAGELINK_EXT, page.text)
    imgfilename = ["".join(i) for i in imgfilename]
    imgfilenameclean = [x for x in imgfilename if "fullxfull" in x]
    if imgfilenameclean == []:
        imgfilenameclean = [x for x in imgfilename if "75x75" in x]

    os.makedirs(Path(path, "Dropshipping Items", title), exist_ok=True)

    for idx, url in enumerate(imgfilenameclean):
        with open(
            Path(path, "Dropshipping Items", title, f"{title}{idx}.jpg"), "wb"
        ) as f:
            response = requests.get(url)
            f.write(response.content)
