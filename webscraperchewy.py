"""CHEWY IMAGE SCRAPER.

Scrapes images from your list on CHEWY

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
from selenium.webdriver.common.action_chains import ActionChains
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
chewy_email = keyring.get_password("CHEWY_EMAIL", user)
chewy_pass = keyring.get_password("CHEWY_PASSWORD", user)

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

PAGES = cf["CHEWY_WEBSCRAPER_PARAMS"]["PAGES"]

CHEWY_LOGIN = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_LOGIN"]

CHEWY_USERNAME_XPATH = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_USERNAME_XPATH"]

CHEWY_PASSWORD_XPATH = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_PASSWORD_XPATH"]

CHEWY_LOGIN_BUTTON_XPATH = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_LOGIN_BUTTON_XPATH"]

CHEWY_LISTS = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_LISTS"]

CHEWY_SOUP_SHIPHOW_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_SOUP_SHIPHOW_EXT"]

CHEWY_SOUP_AUTOSHIPPRICE_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"][
    "CHEWY_SOUP_AUTOSHIPPRICE_EXT"
]

CHEWY_SOUP_COLORLIST_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_SOUP_COLORLIST_EXT"]

CHEWY_SOUP_COLORLIST_FINDALL_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"][
    "CHEWY_SOUP_COLORLIST_FINDALL_EXT"
]

CHEWY_SOUP_SIZELIST_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_SOUP_SIZELIST_EXT"]

CHEWY_SOUP_SIZELIST_FINDALL_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"][
    "CHEWY_SOUP_SIZELIST_FINDALL_EXT"
]

CHEWY_XPATH_CLICKMYFAV = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_XPATH_CLICKMYFAV"]

CHEWY_SOUP_IMAGEFILE_EXT = cf["CHEWY_WEBSCRAPER_PARAMS"]["CHEWY_SOUP_IMAGEFILE_EXT"]

# Configure ChromeOptions
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-CHEWY")
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
        Path(path, "chewy responses", f"responsechewywishlist{i}.html"),
        "w",
        encoding="utf-8",
    ) as fp:
        fp.write(response)


def save_html_to_file(response, title):
    """Save response to response.html."""
    with open(
        Path(path, "chewy responses", f"responsechewy{title}.html"),
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
in_stock = []
extracted_price = []
new_auto_ship_price = []
new_colors = []
new_sizes = []

# title = 'Among us Kid & Young Adult Cotton Hoodie Sweatshirt Each S-M Only'
# page = requests.get('https://www.aliexpress.com/item/1005001841220476.html?')
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
            elem = driver.find_element_by_xpath("//*")
            source_code = elem.get_attribute("outerHTML")
            save_html_to_file(source_code, idx)
            soup = BeautifulSoup(source_code, "lxml")
            json_content = soup.find_all(type="application/ld+json")
            content = json.loads(json_content[0].contents[0])

        try:
            title = (
                content[0]["name"]
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
                content[0]["description"]
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
            description = ""
            pass

        new_descriptions.append(description)

        try:
            price = (
                content[0]["offers"]["highPrice"]
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
            ship_how = str(soup.find(CHEWY_SOUP_SHIPHOW_EXT).text).replace(
                "\n                            ", " "
            )
        except Exception as e:
            print(e)
            ship_how = ""
            pass

        new_ship_how.append(ship_how)

        try:
            auto_ship_price = str(soup.find(CHEWY_SOUP_AUTOSHIPPRICE_EXT).text)
        except Exception as e:
            print(e)
            auto_ship_price = ""
            pass

        new_auto_ship_price.append(auto_ship_price)

        try:
            color_list = soup.find(CHEWY_SOUP_COLORLIST_EXT).findAll(
                CHEWY_SOUP_COLORLIST_FINDALL_EXT
            )
            colors = [
                color_list[i].text
                for i in range(0, len(color_list))
                if color_list[i].text != "Click to select "
            ]
        except Exception as e:
            print(e)
            colors = ""
            pass

        new_colors.append(colors)

        try:
            size_list = soup.find(CHEWY_SOUP_SIZELIST_EXT).findAll(
                CHEWY_SOUP_SIZELIST_FINDALL_EXT
            )
            sizes = [
                size_list[i].text
                for i in range(0, len(size_list))
                if size_list[i].text != "Click to select "
            ]
        except Exception as e:
            print(e)
            sizes = ""
            pass

        new_sizes.append(sizes)

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

    new_items_df.to_csv(Path(path, "Dropshipping Items", "new_items_chewy.csv"))


def linkscraperchewy():
    """Extract Links from CHEWY list."""
    # Go to the website
    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:
        action = ActionChains(driver)
        if os.path.exists(".profile-CHEWY") is False:
            # Logging IN
            driver.get(CHEWY_LOGIN)
            time.sleep(random.randint(2, 3))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .click()
            )
            username = username
            action.key_down(Keys.CONTROL).send_keys("A").key_up(Keys.CONTROL).perform()
            time.sleep(random.uniform(0.5, 0.8))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .send_keys(Keys.BACKSPACE)
            )
            time.sleep(random.uniform(0.5, 0.8))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .send_keys(chewy_email)
            )
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_PASSWORD_XPATH)))
                .send_keys(chewy_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_LOGIN_BUTTON_XPATH)))
                .click()
            )
            login = login
            time.sleep(random.randint(10, 15))

        driver.get(CHEWY_LISTS)
        time.sleep(random.randint(2, 3))
        username = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
            .click()
        )
        action.key_down(Keys.CONTROL).send_keys("A").key_up(Keys.CONTROL).perform()
        time.sleep(random.uniform(0.5, 0.8))
        username = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
            .send_keys(Keys.BACKSPACE)
        )
        time.sleep(random.uniform(0.5, 0.8))
        username = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
            .send_keys(chewy_email)
        )
        time.sleep(random.uniform(0.15, 0.4))
        password = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, CHEWY_PASSWORD_XPATH)))
            .send_keys(chewy_pass)
        )
        # time.sleep(random.randint(30,40))
        time.sleep(random.uniform(0.15, 0.4))
        login = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, CHEWY_LOGIN_BUTTON_XPATH)))
            .click()
        )
        time.sleep(random.randint(10, 15))

        try:
            click_my_fav = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_XPATH_CLICKMYFAV)))
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
        # links = soup.findAll("div", attrs={"class": "buyitagain__data"})
        for link in soup.findAll("div", attrs={"class": "buyitagain__data"}):
            extracted_links.append(
                "https://www.chewy.com" + link.findAll("a")[0]["href"]
            )

            if link.findAll("div", attrs={"class": "availability"}) != []:
                in_stock.append(
                    (
                        soup.findAll("div", attrs={"class": "availability"})[0].text
                    ).replace("\n", "")
                )
            else:
                in_stock.append("")

    product_list = pd.read_excel(
        Path(
            path,
            "Dropshipping Items",
            "DROPSHIPPING_SPREADSHEET.xlsx",
            sheet_name="PRODUCT_LIST",
        )
    )
    not_new_items = list(product_list["Link"])

    tup = [(extracted_links[i], in_stock[i]) for i in range(0, len(extracted_links))]
    new_items = [i[0] for i in tup if i[1] == ""]
    new_items = [link for link in new_items if link not in not_new_items]

    listingscraper(new_items)


def imagewebscraperchewy(URL, title):
    """Webscrape Images from Chewy."""
    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:
        action = ActionChains(driver)
        # Logging IN
        driver.get(CHEWY_LOGIN)
        time.sleep(random.randint(10, 15))
        time.sleep(random.uniform(0.5, 0.8))
        if os.path.exists(".profile-CHEWY") is False:
            time.sleep(random.randint(2, 3))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .click()
            )
            username = username
            action.key_down(Keys.CONTROL).send_keys("A").key_up(Keys.CONTROL).perform()
            time.sleep(random.uniform(0.5, 0.8))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .send_keys(Keys.BACKSPACE)
            )
            time.sleep(random.uniform(0.5, 0.8))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_USERNAME_XPATH)))
                .send_keys(chewy_email)
            )
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_PASSWORD_XPATH)))
                .send_keys(chewy_pass)
            )
            password = password
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, CHEWY_LOGIN_BUTTON_XPATH)))
                .click()
            )
            login = login
            time.sleep(random.randint(10, 15))
        # Save the cookies in a file
        with open(Path(path, "cookieschewy.dat", "wb")) as f:
            pickle.dump(driver.get_cookies(), f)

    saved_cookies_list = load_cookies(Path(path, "cookieschewy.dat"))

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
        soup.findAll(CHEWY_SOUP_IMAGEFILE_EXT)[idx]["src"]
        for idx in range(0, len(soup.findAll(CHEWY_SOUP_IMAGEFILE_EXT)))
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
