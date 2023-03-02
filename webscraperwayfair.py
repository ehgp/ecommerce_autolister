"""WAYFAIR IMAGE SCRAPER.

Scrapes images from your list on WAYFAIR

Author: ehgp
"""
import datetime as dt
import json
import logging
import logging.config
import os
import pickle
import random
import re
import string
import sys
import time
from getpass import getuser
from os import listdir
from os.path import isfile, join
from pathlib import Path

import chromedriver_autoinstaller
import keyring
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def format_filename(s):
    """Take a string and return a valid filename constructed from the string.

    Uses a whitelist approach: any characters not present in valid_chars are
    removed.

    Note: this method may produce invalid filenames such as ``, `.` or `..`
    When I use this method I prepend a date string like '2009_01_15_19_46_32_'
    and append a file extension like '.txt', so I avoid the potential of using
    an invalid filename.

    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = "".join(re.sub("[^A-Za-z0-9]+", " ", c) for c in s if c in valid_chars)
    filename = " ".join(filename.split())
    return filename


def _load_config():
    """Load the configuration yaml and return dictionary of setttings.

    Returns:
        yaml as a dictionary.
    """
    config_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(config_path, "xpath_params.yaml")
    with open(config_path, "r") as config_file:
        config_defs = yaml.safe_load(config_file.read())

    if config_defs.values() is None:
        raise ValueError("parameters yaml file incomplete")

    return config_defs


# Creds
user = getuser()
wayfair_email = keyring.get_password("WAYFAIR_EMAIL", user)
wayfair_pass = keyring.get_password("WAYFAIR_PASSWORD", user)

# Paths
path = Path(os.getcwd())
# binary_path = Path(path, "chromedriver.exe")
chromedriver_autoinstaller.install()
dropship_sh_path = Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx")
dropship_path = Path(path, "Dropshipping Items")

# Logging
Path("log").mkdir(parents=True, exist_ok=True)
log_config = Path(path, "log_config.yaml")
timestamp = "{:%Y_%m_%d_%H_%M_%S}".format(dt.datetime.now())
with open(log_config, "r") as log_file:
    config_dict = yaml.safe_load(log_file.read())
    # Append date stamp to the file name
    log_filename = config_dict["handlers"]["file"]["filename"]
    base, extension = os.path.splitext(log_filename)
    base2 = "_" + os.path.splitext(os.path.basename(__file__))[0] + "_"
    log_filename = "{}{}{}{}".format(base, base2, timestamp, extension)
    config_dict["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)

cf = _load_config()

DEFAULT_HEADERS = cf["GENERAL_PARAMS"]["DEFAULT_HEADERS"]

PAGES = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["PAGES"]

WAYFAIR_LOGIN = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_LOGIN"]

WAYFAIR_USERNAME_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_USERNAME_XPATH"]

WAYFAIR_PASSWORD_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_PASSWORD_XPATH"]

WAYFAIR_LOGIN_BUTTON_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"][
    "WAYFAIR_LOGIN_BUTTON_XPATH"
]

WAYFAIR_LISTS = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_LISTS"]

WAYFAIR_WT_DIM_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_WT_DIM_XPATH"]

WAYFAIR_SPEC_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_SPEC_XPATH"]

WAYFAIR_SOUP_SHIPPRICE_EXT = cf["WAYFAIR_WEBSCRAPER_PARAMS"][
    "WAYFAIR_SOUP_SHIPPRICE_EXT"
]

WAYFAIR_SOUP_SHIPHOW_EXT = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_SOUP_SHIPHOW_EXT"]

WAYFAIR_FAVLIST_XPATH = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_FAVLIST_XPATH"]

WAYFAIR_SOUP_LINK_EXT = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_SOUP_LINK_EXT"]

WAYFAIR_SOUP_IMGLINK_EXT = cf["WAYFAIR_WEBSCRAPER_PARAMS"]["WAYFAIR_SOUP_IMGLINK_EXT"]

# Configure ChromeOptions
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-WAYFAIR")
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
options.add_argument("--disable-infobars")  # disabling infobars
options.add_argument("--disable-extensions")  # disabling extensions
options.add_argument("--disable-gpu")  # applicable to windows os only
options.add_argument("--disable-dev-shm-usage")  # overcome limited resource problems
options.add_argument("--remote-debugging-port=9222")


def save_to_file_wishlist(response, i):
    """Save response to response.html."""
    with open(
        Path(path, "wayfair responses", f"responsewayfairwishlist{i}.html"),
        "w",
        encoding="utf-8",
    ) as fp:
        fp.write(response)


def save_html_to_file(response, title):
    """Save response to response.html."""
    with open(
        Path(path, "wayfair responses", f"responsewayfair{title}.html"),
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
new_prices = []
new_ship_prices = []
new_ship_how = []
extracted_links = []


# title = 'Among us Kid & Young Adult Cotton Hoodie Sweatshirt Each S-M Only'
# page = requests.get('https://www.WAYFAIRexpress.com/item/1005001841220476.html?')
# soup = BeautifulSoup(page.text, 'lxml')
# save_html_to_file(page.text,title)


def listingscraper(new_items):
    """Scrape listing title, description, price, ship price."""
    for idx, link in enumerate(new_items):
        with webdriver.Chrome(
            # executable_path=binary_path,
            options=options
        ) as driver:
            driver.get(link)
            time.sleep(random.randint(10, 15))
            click_wt_and_dim = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_WT_DIM_XPATH)))
                .click()
            )
            click_wt_and_dim = click_wt_and_dim
            click_spec = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_SPEC_XPATH)))
                .click()
            )
            click_spec = click_spec
            time.sleep(random.randint(5, 10))
            elem = driver.find_element_by_xpath("//*")
            source_code = elem.get_attribute("outerHTML")
            save_html_to_file(source_code, idx)
            soup = BeautifulSoup(source_code, "lxml")
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
                .replace("Wayfair", "")
                .replace("WAYFAIR", "")
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
                .replace("Wayfair", "")
                .replace("WAYFAIR", "")
            )
            heads = [item.text for item in soup.find_all("dt")]
            details = [item.text for item in soup.find_all("dd")]
            new_details = []
            for i in range(0, len(heads)):
                new_details.append(heads[i] + ": " + details[i])
            new_details = " ".join(new_details)
            new_details.replace("Details about  \xa0", "").replace(
                "from China", ""
            ).replace("Worldwide", "").replace("Etsy", "").replace("etsy", "").replace(
                "ETSY", ""
            ).replace(
                "eBay", ""
            ).replace(
                "ebay", ""
            ).replace(
                "EBAY", ""
            ).replace(
                "AliExpress", ""
            ).replace(
                "aliexpress", ""
            ).replace(
                "ALIEXPRESS", ""
            ).replace(
                "LIFETIME WARRANTY", ""
            ).replace(
                "WARRANTY", ""
            ).replace(
                "lifetime warranty", ""
            ).replace(
                "|", ""
            ).replace(
                "\n", " "
            ).replace(
                "\xa0", ""
            ).replace(
                " Store Categories Store Categories ", ""
            ).replace(
                "US $", ""
            ).replace(
                "Return", ""
            ).replace(
                "return", ""
            ).replace(
                "Refund", ""
            ).replace(
                "refund", ""
            ).replace(
                "Wayfair", ""
            ).replace(
                "WAYFAIR", ""
            )
        except Exception as e:
            print(e)
            description = ""
            new_details = ""
            pass

        new_descriptions.append(description + " " + new_details)

        try:
            price = (
                str(content["offers"]["price"])
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
                .replace("Wayfair", "")
                .replace("WAYFAIR", "")
            )
        except Exception as e:
            print(e)
            price = ""
            pass

        new_prices.append(price)

        try:
            ship_price = (
                str(soup.find(WAYFAIR_SOUP_SHIPPRICE_EXT).text)
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
                .replace("Wayfair", "")
                .replace("WAYFAIR", "")
            )
        except Exception as e:
            print(e)
            ship_price = ""
            pass

        new_ship_prices.append(ship_price)

        try:
            ship_how = str(soup.find(WAYFAIR_SOUP_SHIPHOW_EXT).text)
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

    new_items.to_csv(Path(path, "Dropshipping Items", "new_items_wayfair.csv"))


def linkscraperwayfair():
    """Extract Links from WAYFAIR list."""
    # Go to the website
    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:

        if os.path.exists(".profile-WAYFAIR") is False:
            # Logging IN
            driver.get(WAYFAIR_LOGIN)
            time.sleep(random.randint(10, 15))
            time.sleep(random.uniform(0.5, 0.8))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_USERNAME_XPATH)))
                .send_keys(wayfair_email)
            )
            username = username
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, WAYFAIR_LOGIN_BUTTON_XPATH))
                )
                .click()
            )
            login = login
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_PASSWORD_XPATH)))
                .send_keys(wayfair_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, WAYFAIR_LOGIN_BUTTON_XPATH))
                )
                .click()
            )
            time.sleep(random.randint(10, 15))

        driver.get(WAYFAIR_LISTS)
        try:
            click_my_fav = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            WAYFAIR_FAVLIST_XPATH,
                        )
                    )
                )
                .click()
            )
            click_my_fav = click_my_fav
            time.sleep(random.randint(5, 8))
        except Exception as e:
            print(e)
            print("lists has no My Favorites")
            pass
        # for x in range(1,PAGES):
        time.sleep(random.randint(5, 8))
        elem = driver.find_element_by_xpath("//*")
        source_code = elem.get_attribute("outerHTML")
        save_to_file_wishlist(source_code, 0)
        soup = BeautifulSoup(source_code, "lxml")
        for link in soup.findAll(WAYFAIR_SOUP_LINK_EXT):
            extracted_links.append(link.get("href").split("?", 1)[0])

    product_list = pd.read_excel(
        Path(path, "Dropshipping Items", "DROPSHIPPING_SPREADSHEET.xlsx"),
        sheet_name="PRODUCT_LIST",
    )
    not_new_items = list(product_list["Link"])

    new_items = [link for link in extracted_links if link not in not_new_items]

    listingscraper(new_items)


def imagewebscraperwayfair(URL, title):
    """Webscrape Images from WAYFAIR."""
    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:

        # Logging IN
        driver.get(WAYFAIR_LOGIN)
        time.sleep(random.randint(10, 15))
        time.sleep(random.uniform(0.5, 0.8))
        if os.path.exists(".profile-WAYFAIR") is False:
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_USERNAME_XPATH)))
                .send_keys(wayfair_email)
            )
            username = username
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, WAYFAIR_LOGIN_BUTTON_XPATH))
                )
                .click()
            )
            login = login
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, WAYFAIR_PASSWORD_XPATH)))
                .send_keys(wayfair_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, WAYFAIR_LOGIN_BUTTON_XPATH))
                )
                .click()
            )
            time.sleep(random.randint(10, 15))
        # Save the cookies in a file
        with open(Path(path, "cookieswayfair.dat"), "wb") as f:
            pickle.dump(driver.get_cookies(), f)

    saved_cookies_list = load_cookies(Path(path, "cookieswayfair.dat"))

    # Set request session
    initial_state = requests.Session()

    initial_state_with_cookies = fix_cookies_and_load_to_requests(
        cookie_list=saved_cookies_list, request_session=initial_state
    )
    time.sleep(random.uniform(0.5, 0.8))
    page = initial_state_with_cookies.get(URL)

    save_html_to_file(page.text, title)

    soup = BeautifulSoup(page.text, "lxml")
    json_content = soup.find_all(type="application/ld+json")
    content = json.loads(json_content[0].contents[0])
    content = content
    imgfilename = [
        soup.findAll(WAYFAIR_SOUP_IMGLINK_EXT)[idx]["src"]
        for idx in range(0, len(soup.findAll(WAYFAIR_SOUP_IMGLINK_EXT)))
    ]

    os.makedirs(Path(path, "Dropshipping Items", title), exist_ok=True)

    for idx, url in enumerate(imgfilename):
        if idx < 10:
            with open(
                Path(path, "Dropshipping Items", title, f"{title}{idx}.jpg"), "wb"
            ) as f:
                time.sleep(random.uniform(0.5, 0.8))
                response = initial_state_with_cookies.get(url)
                f.write(response.content)
        else:
            pass
