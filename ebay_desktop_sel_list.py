"""Selenium EBAY Marketplace Dropshipping Automator (SEMPDA).

Allows user to leverage an excel sheet to automatically add products to EBAY

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
import pyautogui
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


# from utils.encryption import create_encrypted_config, load_encrypted_config
# os.makedirs(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET', exist_ok = True)
# os.rmdir(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET')

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

logger.info("Get Credentials")
user = getuser()
ebay_email = keyring.get_password("EBAY_EMAIL", user)
ebay_pass = keyring.get_password("EBAY_PASSWORD", user)
if (ebay_email or ebay_pass) is None:
    logger.info("Incomplete credentials")
    exit()

cf = _load_config()

DEFAULT_HEADERS = cf["GENERAL_PARAMS"]["DEFAULT_HEADERS"]

EBAY_LOGIN = cf["EBAY_PARAMS"]["EBAY_LOGIN"]

EBAY_USERNAME_XPATH = cf["EBAY_PARAMS"]["EBAY_USERNAME_XPATH"]

EBAY_PASSWORD_XPATH = cf["EBAY_PARAMS"]["EBAY_PASSWORD_XPATH"]

EBAY_LOGIN_BUTTON_XPATH = cf["EBAY_PARAMS"]["EBAY_LOGIN_BUTTON_XPATH"]

EBAY_LISTING = cf["EBAY_PARAMS"]["EBAY_LISTING"]

EBAY_START_LISTING = cf["EBAY_PARAMS"]["EBAY_START_LISTING"]

EBAY_IMAGE_UPLOAD_XPATH = cf["EBAY_PARAMS"]["EBAY_IMAGE_UPLOAD_XPATH"]

EBAY_TITLE_XPATH = cf["EBAY_PARAMS"]["EBAY_TITLE_XPATH"]

EBAY_WHO_MADE = cf["EBAY_PARAMS"]["EBAY_WHO_MADE"]

EBAY_WHO_MADE_SOMEONE_ELSE = cf["EBAY_PARAMS"]["EBAY_WHO_MADE_SOMEONE_ELSE"]

EBAY_WHAT_IS_IT = cf["EBAY_PARAMS"]["EBAY_WHAT_IS_IT"]

EBAY_WHAT_IS_IT_PRODUCT = cf["EBAY_PARAMS"]["EBAY_WHAT_IS_IT_PRODUCT"]

EBAY_WHEN_MADE = cf["EBAY_PARAMS"]["EBAY_WHEN_MADE"]

EBAY_WHEN_MADE_TO_ORDER = cf["EBAY_PARAMS"]["EBAY_WHEN_MADE_TO_ORDER"]

EBAY_CTGRY_XPATH = cf["EBAY_PARAMS"]["EBAY_CTGRY_XPATH"]

EBAY_RENEW_LISTING = cf["EBAY_PARAMS"]["EBAY_RENEW_LISTING"]

EBAY_DES_XPATH = cf["EBAY_PARAMS"]["EBAY_DES_XPATH"]

EBAY_DES1_XPATH = cf["EBAY_PARAMS"]["EBAY_DES1_XPATH"]

EBAY_PRICE_XPATH = cf["EBAY_PARAMS"]["EBAY_PRICE_XPATH"]

EBAY_QTY_XPATH = cf["EBAY_PARAMS"]["EBAY_QTY_XPATH"]

EBAY_SHIP_XPATH = cf["EBAY_PARAMS"]["EBAY_SHIP_XPATH"]

EBAY_PUBLISH_XPATH = cf["EBAY_PARAMS"]["EBAY_PUBLISH_XPATH"]

EBAY_CONFIRM_XPATH = cf["EBAY_PARAMS"]["EBAY_CONFIRM_XPATH"]

logger.info("Configure ChromeOptions")
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--no-sandbox")  # Bypass OS security model
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
options.add_argument("--disable-infobars")  # disabling infobars
options.add_argument("--disable-extensions")  # disabling extensions
options.add_argument("--disable-gpu")  # applicable to windows os only
options.add_argument("--disable-dev-shm-usage")  # overcome limited resource problems
options.add_argument("--remote-debugging-port=9222")

product_list = pd.read_excel(dropship_sh_path, sheet_name="PRODUCT_LIST")
items_to_list = product_list[
    (product_list["UNLISTED"] == "T") & (product_list["SUPPLIER"] != "EBAY")
].reset_index(drop=True)

logger.info("Open Browser")
if len(items_to_list) == 0:
    logger.info("no products to list")
    exit()

for i in range(0, len(items_to_list)):

    all_image_files_list = []
    all_images = []
    pricebought = ""
    priceship = ""

    # if os.path.exists(Path(dropship_path, items_to_list["Title"][i])) is False:

    #     if items_to_list["SUPPLIER"][i].upper() == "ALIEXPRESS":
    #         imagewebscraperali(items_to_list["Link"][i], items_to_list["Title"][i])

    #     elif items_to_list["SUPPLIER"][i].upper() == "EBAY":
    #         imagewebscraperebay(items_to_list["Link"][i], items_to_list["Title"][i])

    #     elif items_to_list["SUPPLIER"][i].upper() == "ETSY":
    #         imagewebscraperetsy(items_to_list["Link"][i], items_to_list["Title"][i])

    #     elif items_to_list["SUPPLIER"][i].upper() == "WAYFAIR":
    #         imagewebscraperwayfair(items_to_list["Link"][i], items_to_list["Title"][i])

    #     elif items_to_list["SUPPLIER"][i].upper() == "CHEWY":
    #         imagewebscraperchewy(items_to_list["Link"][i], items_to_list["Title"][i])
    #     else:
    #         logger.info("No Supplier Matched")

    # else:

    #     all_images = [
    #         f
    #         for f in listdir(Path(dropship_path, items_to_list["Title"][i]))
    #         if isfile(join(Path(dropship_path, items_to_list["Title"][i]), f))
    #     ]

    #     all_image_files_list = []
    #     for idx, imagename in enumerate(all_images):
    #         all_image_files_list.append(
    #             Path(dropship_path, items_to_list["Title"][i], imagename)
    #         )

    with webdriver.Chrome(
        # executable_path=binary_path,
        options=options
    ) as driver:
        try:
            logger.info("Log In")
            time.sleep(random.randint(3, 5))
            driver.get(EBAY_LOGIN)
            time.sleep(random.randint(3, 5))
            email = driver.find_element_by_id("userid").send_keys(ebay_email)
            time.sleep(random.uniform(0.15, 0.4))
            continue_btn = driver.find_element_by_id("signin-continue-btn").click()
            time.sleep(random.randint(3, 5))
            password = driver.find_element_by_id("pass").send_keys(ebay_pass)
            time.sleep(random.uniform(0.15, 0.4))
            login = driver.find_element_by_id("sgnBt").click()

            logger.info("Redirect to EBAY LISTING CREATE")
            time.sleep(random.randint(3, 5))
            driver.get(EBAY_LISTING)
            time.sleep(random.randint(3, 5))
            start_listing = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_START_LISTING)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            start_listing = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_START_LISTING)))
                .click()
            )

            logger.info("enter images")
            time.sleep(random.randint(3, 5))
            fileInput = driver.find_element_by_xpath(EBAY_IMAGE_UPLOAD_XPATH).click()
            time.sleep(random.randint(3, 5))
            pyautogui.hotkey("alt", "d")
            time.sleep(random.uniform(0.15, 0.4))
            pyautogui.write(Path(dropship_path, items_to_list["Title"][i]))
            time.sleep(random.uniform(0.15, 0.4))
            pyautogui.press("enter")
            for x in range(4):
                time.sleep(random.uniform(0.15, 0.4))
                pyautogui.press("tab")
                time.sleep(random.uniform(0.15, 0.4))
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(0.15, 0.4))
            pyautogui.press("enter")

            logger.info("enter title")
            time.sleep(random.randint(3, 5))
            title = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_TITLE_XPATH)))
                .send_keys(items_to_list["Title"][i])
            )
            logger.info("RENEW LISTING MANUAL")
            renew_manual = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_RENEW_LISTING)))
                .click()
            )
            logger.info("ABOUT THIS LISTING")
            time.sleep(random.randint(3, 5))
            who_made = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_WHO_MADE)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            someone_else_made = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable((By.XPATH, EBAY_WHO_MADE_SOMEONE_ELSE))
                )
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            what_is_it = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_WHAT_IS_IT)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            what_is_it_product = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_WHAT_IS_IT_PRODUCT)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            when_made = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_WHEN_MADE)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            when_made_to_order = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_WHEN_MADE_TO_ORDER)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            logger.info("CATEGORY")
            ctgry = driver.find_element_by_xpath(EBAY_CTGRY_XPATH).send_keys(
                items_to_list["Title"][i]
            )
            ctgry = driver.find_element_by_xpath(EBAY_CTGRY_XPATH).send_keys(Keys.ENTER)
            time.sleep(random.randint(3, 5))
            logger.info("DESCRIPTION")
            description = driver.find_element_by_xpath(EBAY_DES_XPATH).send_keys(
                Keys.END
            )
            time.sleep(random.uniform(0.15, 0.4))
            description = driver.find_element_by_xpath(EBAY_DES1_XPATH).send_keys(
                Keys.CLEAR
            )
            time.sleep(random.uniform(0.15, 0.4))
            description = driver.find_element_by_xpath(EBAY_DES1_XPATH).send_keys(
                items_to_list["Description"][i]
            )
            time.sleep(random.randint(3, 5))
            time.sleep(random.randint(10, 15))
            logger.info("PRICE")
            price = driver.find_element_by_xpath(EBAY_PRICE_XPATH).send_keys(
                Keys.BACKSPACE
            )
            price = driver.find_element_by_xpath(EBAY_PRICE_XPATH).send_keys(
                int(items_to_list["Price"][i])
            )
            time.sleep(random.uniform(0.15, 0.4))
            logger.info("QUANTITY")
            qty = driver.find_element_by_xpath(EBAY_QTY_XPATH).send_keys(Keys.BACKSPACE)
            qty = driver.find_element_by_xpath(EBAY_QTY_XPATH).send_keys(
                int(items_to_list["Quantity"][i])
            )
            logger.info("SHIPPING DEFAULT")
            time.sleep(random.uniform(0.15, 0.4))
            ship_default = driver.find_element_by_xpath(EBAY_SHIP_XPATH).send_keys(
                Keys.END
            )
            time.sleep(random.uniform(0.15, 0.4))
            ship_default = driver.find_element_by_xpath(EBAY_SHIP_XPATH).click()
            time.sleep(random.uniform(0.15, 0.4))
            # PUBLISH
            publish = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_PUBLISH_XPATH)))
                .click()
            )
            time.sleep(random.uniform(0.15, 0.4))
            logger.info("CONFIRM")
            confirm = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, EBAY_CONFIRM_XPATH)))
                .click()
            )
            time.sleep(random.randint(3, 5))
            driver.quit()
            shutil.rmtree(".profile-EBAY")
        except Exception as e:
            driver.quit()
            logger.info(e)
            shutil.rmtree(".profile-EBAY")
