"""WAYFAIR IMAGE SCRAPER.

Scrapes images from your list on WAYFAIR

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
wayfair_email = keyring.get_password("WAYFAIR_EMAIL", user)
wayfair_pass = keyring.get_password("WAYFAIR_PASSWORD", user)

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
    base2 = "webscraperwayfair"
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

WAYFAIR_LOGIN = "https://www.wayfair.com/v/account/authentication/login?"

WAYFAIR_USERNAME_XPATH = "//input[@id='textInput-0']"

WAYFAIR_PASSWORD_XPATH = "//input[@id='textInput-1']"

WAYFAIR_LOGIN_BUTTON_XPATH = "//button[@type='submit']"

WAYFAIR_LISTS = "https://www.wayfair.com/lists"

WAYFAIR_WT_DIM_XPATH = "//div[text()='Weights & Dimensions']"

WAYFAIR_SPEC_XPATH = "//div[text()='Specifications']"

WAYFAIR_SOUP_SHIPPRICE_EXT = '"span", attrs={"class": "ShippingHeadline-text"}'

WAYFAIR_SOUP_SHIPHOW_EXT = '"div", attrs={"data-enzyme-id": "FullWidthShippingOptions"}'

WAYFAIR_FAVLIST_XPATH = "//div[@class='ListCard-name'][text()='My Favorites']"

WAYFAIR_SOUP_LINK_EXT = '"a", attrs={"class": "pl-ProductCard-productCardElement"}'

WAYFAIR_SOUP_IMGLINK_EXT = '"img", attrs={"class": "pl-FluidImage-image"}'

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
        with webdriver.Chrome(executable_path=binary_path, options=options) as driver:
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
    with webdriver.Chrome(executable_path=binary_path, options=options) as driver:

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
    with webdriver.Chrome(executable_path=binary_path, options=options) as driver:

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
