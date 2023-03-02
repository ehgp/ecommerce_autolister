"""Selenium FB Marketplace Dropshipping Automator (SFBMPDA).

Allows user to leverage an excel sheet to automatically add products to FBMP

Author: ehgp
"""
import datetime as dt
import logging
import logging.config
import os
import random
import re
import shutil
import string
import time
from getpass import getuser
from os import listdir
from os.path import isfile, join
from pathlib import Path

import chromedriver_autoinstaller
import keyring
import pandas as pd
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webscraperali import imagewebscraperali
from webscraperchewy import imagewebscraperchewy
from webscraperebay import imagewebscraperebay
from webscraperetsy import imagewebscraperetsy
from webscraperwayfair import imagewebscraperwayfair


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

# from utils.encryption import create_encrypted_config, load_encrypted_config
# os.makedirs(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET', exist_ok = True)
# os.rmdir(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET')

logger.info("Get Credentials")
user = getuser()
fb_email = keyring.get_password("FACEBOOK_EMAIL", user)
fb_pass = keyring.get_password("FACEBOOK_PASSWORD", user)
if (fb_email or fb_pass) is None:
    logger.info("Incomplete credentials")
    exit()

DEFAULT_HEADERS = cf["GENERAL_PARAMS"]["DEFAULT_HEADERS"]

FB_LOGIN = cf["FB_PARAMS"]["FB_LOGIN"]

FB_LISTING = cf["FB_PARAMS"]["FB_LISTING"]

FB_IMAGE_UPLOAD_XPATH = cf["FB_PARAMS"]["FB_IMAGE_UPLOAD_XPATH"]

FB_TITLE_XPATH = cf["FB_PARAMS"]["FB_TITLE_XPATH"]

FB_AVAIL_QTY_XPATH = cf["FB_PARAMS"]["FB_AVAIL_QTY_XPATH"]

FB_PRICE_XPATH = cf["FB_PARAMS"]["FB_PRICE_XPATH"]

FB_PRICE_ONE_XPATH = cf["FB_PARAMS"]["FB_PRICE_ONE_XPATH"]

FB_CAT_XPATH = cf["FB_PARAMS"]["FB_CAT_XPATH"]

FB_CAT_MISC_XPATH = cf["FB_PARAMS"]["FB_CAT_MISC_XPATH"]

FB_COND_XPATH = cf["FB_PARAMS"]["FB_COND_XPATH"]

FB_COND_NEW_XPATH = cf["FB_PARAMS"]["FB_COND_NEW_XPATH"]

FB_DESCRIPTION_XPATH = cf["FB_PARAMS"]["FB_DESCRIPTION_XPATH"]

FB_TAGS_XPATH = cf["FB_PARAMS"]["FB_TAGS_XPATH"]

FB_NEXT_PAGE_SHIPPING_XPATH = cf["FB_PARAMS"]["FB_NEXT_PAGE_SHIPPING_XPATH"]

FB_SHIPPING_TYPE_XPATH = cf["FB_PARAMS"]["FB_SHIPPING_TYPE_XPATH"]

FB_SHIPPING_ONLY_XPATH = cf["FB_PARAMS"]["FB_SHIPPING_ONLY_XPATH"]

FB_SHIPPING_OPT_ACT_XPATH = cf["FB_PARAMS"]["FB_SHIPPING_OPT_ACT_XPATH"]

FB_SHIPPING_OPT_OWN_XPATH = cf["FB_PARAMS"]["FB_SHIPPING_OPT_OWN_XPATH"]

FB_SHIPPING_RATE_CLICK_INPUT_XPATH = cf["FB_PARAMS"][
    "FB_SHIPPING_RATE_CLICK_INPUT_XPATH"
]

FB_SHIPPING_RATE_CLICK_INPUT_SINGLE_XPATH = cf["FB_PARAMS"][
    "FB_SHIPPING_RATE_CLICK_INPUT_SINGLE_XPATH"
]

FB_SHIPPING_FREE_XPATH = cf["FB_PARAMS"]["FB_SHIPPING_FREE_XPATH"]

FB_NEXT_PAGE_OFFER_XPATH = cf["FB_PARAMS"]["FB_NEXT_PAGE_OFFER_XPATH"]

FB_NEXT_PAGE_PUBLISH_XPATH = cf["FB_PARAMS"]["FB_NEXT_PAGE_PUBLISH_XPATH"]

FB_PUBLISH_BUTTON = cf["FB_PARAMS"]["FB_PUBLISH_BUTTON"]

logger.info("Configure ChromeOptions")
options = Options()
options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-FB")
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
options.add_argument("--no-sandbox")  # Bypass OS security model
options.add_argument("--disable-dev-shm-usage")  # overcome limited resource problems
options.add_argument("--remote-debugging-port=9222")

product_list = pd.read_excel(dropship_sh_path, sheet_name="PRODUCT_LIST")
items_to_list = product_list[product_list["UNLISTED"] == "T"].reset_index(drop=True)

logger.info("Open Browser")
if len(items_to_list) == 0:
    logger.info("no products to list")
    exit()

for i in range(0, len(items_to_list)):

    all_image_files_list = []
    all_images = []
    pricebought = ""
    priceship = ""
    description = ""

    if os.path.exists(Path(dropship_path, items_to_list["Title"][i])) is False:

        if items_to_list["SUPPLIER"][i].upper() == "ALIEXPRESS":
            imagewebscraperali(items_to_list["Link"][i], items_to_list["Title"][i])

        elif items_to_list["SUPPLIER"][i].upper() == "EBAY":
            imagewebscraperebay(items_to_list["Link"][i], items_to_list["Title"][i])

        elif items_to_list["SUPPLIER"][i].upper() == "ETSY":
            imagewebscraperetsy(items_to_list["Link"][i], items_to_list["Title"][i])

        elif items_to_list["SUPPLIER"][i].upper() == "WAYFAIR":
            imagewebscraperwayfair(items_to_list["Link"][i], items_to_list["Title"][i])

        elif items_to_list["SUPPLIER"][i].upper() == "CHEWY":
            imagewebscraperchewy(items_to_list["Link"][i], items_to_list["Title"][i])
        else:
            logger.info("No Supplier Matched")

    else:

        all_images = [
            f
            for f in listdir(Path(dropship_path, items_to_list["Title"][i]))
            if isfile(join(Path(dropship_path, items_to_list["Title"][i]), f))
        ]

        all_image_files_list = []
        for idx, imagename in enumerate(all_images):
            all_image_files_list.append(
                Path(dropship_path, items_to_list["Title"][i], imagename)
            )

    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:
        try:
            logger.info("Log In")
            driver.get(FB_LOGIN)
            time.sleep(random.uniform(0.15, 0.4))
            email = driver.find_element_by_id("email").send_keys(fb_email)
            time.sleep(random.uniform(0.15, 0.4))
            password = driver.find_element_by_id("pass").send_keys(fb_pass)
            time.sleep(random.uniform(0.15, 0.4))
            driver.find_element_by_name("login").click()
            time.sleep(random.uniform(0.15, 0.4))

            logger.info("Redirect to fb marketplace")
            time.sleep(random.randint(3, 5))
            driver.get(FB_LISTING)
            time.sleep(random.randint(3, 5))
            logger.info("enter images")
            time.sleep(random.randint(3, 5))
            fileInput = driver.find_element_by_xpath(FB_IMAGE_UPLOAD_XPATH)
            driver.execute_script("arguments[0].style.display = 'block';", fileInput)
            images = " \n ".join(all_image_files_list[:10])
            fileInput.send_keys(images)
            # os.rmdir(Path(dropship_path, items_to_list["Title"][i]))
            logger.info("enter title")
            time.sleep(random.randint(3, 5))
            title = driver.find_element_by_xpath(FB_TITLE_XPATH).send_keys(
                "✅ New " + format_filename(items_to_list["Title"][i])[:70]
            )

            logger.info("enter quantity")
            time.sleep(random.uniform(0.15, 0.4))
            qty = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_AVAIL_QTY_XPATH)))
                .send_keys(Keys.BACKSPACE)
            )
            time.sleep(random.uniform(0.15, 0.4))
            qty = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_AVAIL_QTY_XPATH)))
                .send_keys(str(int(items_to_list["Quantity"][i])))
            )

            logger.info("enter price")
            time.sleep(random.uniform(0.15, 0.4))
            if int(items_to_list["Quantity"][i]) != 1:
                price = (
                    WebDriverWait(driver, 10)
                    .until(EC.element_to_be_clickable((By.XPATH, FB_PRICE_XPATH)))
                    .send_keys(Keys.BACKSPACE)
                )
                time.sleep(random.uniform(0.15, 0.4))
                price = (
                    WebDriverWait(driver, 10)
                    .until(EC.element_to_be_clickable((By.XPATH, FB_PRICE_XPATH)))
                    .send_keys(str(int(items_to_list["Price"][i])))
                )

            if int(items_to_list["Quantity"][i]) == 1:
                price = (
                    WebDriverWait(driver, 10)
                    .until(EC.element_to_be_clickable((By.XPATH, FB_PRICE_ONE_XPATH)))
                    .send_keys(Keys.BACKSPACE)
                )
                time.sleep(random.uniform(0.15, 0.4))
                price = (
                    WebDriverWait(driver, 10)
                    .until(EC.element_to_be_clickable((By.XPATH, FB_PRICE_ONE_XPATH)))
                    .send_keys(str(int(items_to_list["Price"][i])))
                )

            logger.info("enter category")
            time.sleep(random.uniform(0.15, 0.4))
            cat = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_CAT_XPATH)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            cat = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_CAT_MISC_XPATH)))
                .send_keys(Keys.ENTER)
            )

            logger.info("enter quality")
            time.sleep(random.uniform(0.15, 0.4))
            qual = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_COND_XPATH)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            qual = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_COND_NEW_XPATH)))
                .send_keys(Keys.ENTER)
            )

            logger.info("enter description")
            time.sleep(random.uniform(0.15, 0.4))
            des = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_DESCRIPTION_XPATH)))
                .send_keys(
                    "✅ New Product ✅ Price for each! Order "
                    + items_to_list["Title"][i]
                    + "! "
                    + format_filename(items_to_list["Description"][i])
                    + """ Free Shipping Available 24/7 No Returns. \
                    USA Only I accept square, paypal, zelle, \
                    facebook pay, bitcoin/ethereum, cash app"""
                )
            )

            logger.info("enter tags")
            time.sleep(random.uniform(0.15, 0.4))
            tags = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_TAGS_XPATH)))
                .send_keys(str(items_to_list["Tags"][i]))
            )
            time.sleep(random.uniform(0.15, 0.4))
            tags = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_TAGS_XPATH)))
                .send_keys(Keys.ENTER)
            )

            logger.info("next page")
            time.sleep(random.uniform(0.4, 0.6))
            nextpage = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, FB_NEXT_PAGE_SHIPPING_XPATH))
                )
                .click()
            )

            logger.info("shipping type")
            time.sleep(random.randint(3, 5))
            ship = (
                WebDriverWait(driver, 20)
                .until(EC.element_to_be_clickable((By.XPATH, FB_SHIPPING_TYPE_XPATH)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            shiponly = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_SHIPPING_ONLY_XPATH)))
                .send_keys(Keys.ENTER)
            )

            logger.info("shipping option label")
            time.sleep(random.uniform(0.15, 0.4))
            freeshiplabel = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, FB_SHIPPING_OPT_ACT_XPATH))
                )
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            ownshiplabel = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, FB_SHIPPING_OPT_OWN_XPATH))
                )
                .send_keys(Keys.ENTER)
            )

            logger.info("shipping rate")
            time.sleep(random.uniform(0.15, 0.4))
            if int(items_to_list["Quantity"][i]) == 1:
                shiprate = (
                    WebDriverWait(driver, 10)
                    .until(
                        EC.element_to_be_clickable(
                            (By.XPATH, FB_SHIPPING_RATE_CLICK_INPUT_SINGLE_XPATH)
                        )
                    )
                    .send_keys(0)
                )
            if int(items_to_list["Quantity"][i]) != 1:
                shiprate = (
                    WebDriverWait(driver, 10)
                    .until(
                        EC.element_to_be_clickable(
                            (By.XPATH, FB_SHIPPING_RATE_CLICK_INPUT_XPATH)
                        )
                    )
                    .send_keys(0)
                )
            time.sleep(random.uniform(0.15, 0.4))
            # driver.execute_script("window.scrollTo(0,1000);")
            # shiprate = ( WebDriverWait(driver, 10)
            # .until(EC.element_to_be_clickable((By.XPATH,FB_SHIPPING_FREE_XPATH)))
            # .click())
            # time.sleep(random.uniform(0.15, 0.4))

            logger.info("next page")
            nextpage = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, FB_NEXT_PAGE_OFFER_XPATH)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))

            logger.info("next page")
            nextpage = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, FB_NEXT_PAGE_PUBLISH_XPATH))
                )
                .click()
            )

            logger.info("publish")
            time.sleep(random.uniform(0.15, 0.4))
            publish = (
                WebDriverWait(driver, 15)
                .until(EC.element_to_be_clickable((By.XPATH, FB_PUBLISH_BUTTON)))
                .click()
            )
            time.sleep(random.randint(3, 5))
            driver.quit()
            shutil.rmtree(".profile-FB")
        except Exception as e:
            driver.quit()
            logger.info(e)
            shutil.rmtree(".profile-FB")
