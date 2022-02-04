"""Selenium ETSY Marketplace Dropshipping Automator (SEMPDA).

Allows user to leverage an excel sheet to automatically add products to ETSY

Author: ehgp
"""
from webscraperali import imagewebscraperali
from webscraperchewy import imagewebscraperchewy
from webscraperebay import imagewebscraperebay
from webscraperetsy import imagewebscraperetsy
from webscraperwayfair import imagewebscraperwayfair
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from getpass import getuser
import time
import logging
import logging.config
import random
import pandas as pd
import os
import string
import re
import sys
import datetime as dt
from os import listdir
from os.path import isfile, join
from pathlib import Path
import yaml
import keyring
import sqlite3
import pyautogui

# from utils.encryption import create_encrypted_config, load_encrypted_config
# os.makedirs(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET', exist_ok = True)
# os.rmdir(str(path) + "\\Dropshipping Items\\"+ 'TESTESTSETESTSET')
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
    base2 = "etsy_desktop_sel_list"
    log_filename = "{}{}{}{}".format(base, base2, timestamp, extension)
    config_dict["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)

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

ETSY_IMAGE_UPLOAD_XPATH = "//form[@id='listing-photo-uploader']"

ETSY_LISTING = (
    "https://www.etsy.com/your/shops/VentureStoreBoutique/tools/listings/create"
)

ETSY_TITLE_XPATH = "//input[@name='title']"

ETSY_WHO_MADE = "//select[@id='who_made']"

ETSY_WHO_MADE_SOMEONE_ELSE = "//option[@value='someone_else']"

ETSY_WHAT_IS_IT = "//select[@id='is_supply']"

ETSY_WHAT_IS_IT_PRODUCT = "//option[@value='0']"

ETSY_WHEN_MADE = "//select[@id='when_made']"

ETSY_WHEN_MADE_TO_ORDER = "//option[@value='made_to_order']"

ETSY_CTGRY_XPATH = "//input[@id='taxonomy-search']"

ETSY_RENEW_LISTING = "/html/body/div[3]/section/div/div[4]/div[1]/div/div/div[2]/div/div/div/div[5]/div[12]/div/fieldset/div[2]/div[1]/div[2]/label/span"

ETSY_DES_XPATH = "//label[@for='description']"

ETSY_DES1_XPATH = "//textarea[@name='description']"

ETSY_PRICE_XPATH = "//input[@name='price-input']"

ETSY_QTY_XPATH = "//input[@name='quantity-input']"

ETSY_SHIP_XPATH = "//label[@for='125349542613']"

ETSY_PUBLISH_XPATH = "//button[@class='btn btn-primary']"

ETSY_CONFIRM_XPATH = "//button[@data-ui='confirm']"

# Configure ChromeOptions
options = Options()
options.page_load_strategy = "eager"
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)
options.add_argument("user-data-dir=.profile-ETSY")
# options.add_argument('--proxy-server=https://'+ self.proxies[0])
# options.add_argument('--proxy-server=http://'+ self.proxies[0])
# options.add_argument('--proxy-server=socks5://'+ self.proxies[0])
options.add_argument("--disable-notifications")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors")
options.add_argument(
    "user-agent = Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
)
# options.add_argument('--headless')
# options.add_argument('--window-size=1910x1080')
# options.add_argument('--proxy-server=http://'+ proxies[0]))

product_list = pd.read_excel(dropship_sh_path, sheet_name="PRODUCT_LIST")
items_to_list = product_list[
    (product_list["UNLISTED"] == "T") & (product_list["SUPPLIER"] != "ETSY")
].reset_index(drop=True)

# OpenBrowser
for i in range(0, len(items_to_list)):

    all_image_files_list = []
    all_images = []
    pricebought = ""
    priceship = ""

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

    with webdriver.Chrome(executable_path=binary_path, options=options) as driver:

        if os.path.exists(".profile-ETSY") is False:
            driver.get(ETSY_LOGIN)
            # Logging IN
            time.sleep(random.uniform(0.15, 0.4))
            username = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_USERNAME_XPATH)))
                .send_keys(etsy_email)
            )
            time.sleep(random.uniform(0.15, 0.4))
            password = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_PASSWORD_XPATH)))
                .send_keys(etsy_pass)
            )
            # time.sleep(random.randint(30,40))
            time.sleep(random.uniform(0.15, 0.4))
            login = (
                WebDriverWait(driver, 10)
                .until(EC.element_to_be_clickable((By.XPATH, ETSY_LOGIN_BUTTON_XPATH)))
                .click()
            )

        # Redirect to ETSY LISTING CREATE
        time.sleep(random.randint(3, 5))
        driver.get(ETSY_LISTING)

        # enter images
        time.sleep(random.randint(3, 5))
        fileInput = driver.find_element_by_xpath(ETSY_IMAGE_UPLOAD_XPATH).click()
        time.sleep(random.randint(3, 5))
        pyautogui.hotkey("alt", "d")
        time.sleep(random.uniform(0.15, 0.4))
        pyautogui.write(items_to_list["Pic_Directory"][i])
        time.sleep(random.uniform(0.15, 0.4))
        pyautogui.press("enter")
        for x in range(4):
            time.sleep(random.uniform(0.15, 0.4))
            pyautogui.press("tab")
            time.sleep(random.uniform(0.15, 0.4))
        pyautogui.hotkey("ctrl", "a")
        time.sleep(random.uniform(0.15, 0.4))
        pyautogui.press("enter")

        # enter title
        time.sleep(random.randint(3, 5))
        title = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_TITLE_XPATH)))
            .send_keys(items_to_list["Title"][i])
        )
        # RENEW LISTING MANUAL
        renew_manual = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_RENEW_LISTING)))
            .click()
        )
        # ABOUT THIS LISTING
        time.sleep(random.randint(3, 5))
        who_made = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHO_MADE)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        someone_else_made = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHO_MADE_SOMEONE_ELSE)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        what_is_it = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHAT_IS_IT)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        what_is_it_product = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHAT_IS_IT_PRODUCT)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        when_made = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHEN_MADE)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        when_made_to_order = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_WHEN_MADE_TO_ORDER)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        # CATEGORY
        ctgry = driver.find_element_by_xpath(ETSY_CTGRY_XPATH).send_keys(
            items_to_list["Title"][i]
        )
        ctgry = driver.find_element_by_xpath(ETSY_CTGRY_XPATH).send_keys(Keys.ENTER)
        time.sleep(random.randint(3, 5))
        # DESCRIPTION
        description = driver.find_element_by_xpath(ETSY_DES_XPATH).send_keys(Keys.END)
        time.sleep(random.uniform(0.15, 0.4))
        description = driver.find_element_by_xpath(ETSY_DES1_XPATH).send_keys(
            Keys.CLEAR
        )
        time.sleep(random.uniform(0.15, 0.4))
        description = driver.find_element_by_xpath(ETSY_DES1_XPATH).send_keys(
            (
                "✅ New Product ✅ Price for each! Order "
                + items_to_list["Title"][i]
                + "! "
                + items_to_list["Description"][i]
                + """ Free Shipping Available 24/7 No Returns. \
                USA Only I accept square, paypal, venmo, zelle, \
                facebook pay, bitcoin/ethereum, cash app"""
            )
        )
        time.sleep(random.randint(3, 5))
        time.sleep(random.randint(10, 15))
        # PRICE
        price = driver.find_element_by_xpath(ETSY_PRICE_XPATH).send_keys(Keys.BACKSPACE)
        price = driver.find_element_by_xpath(ETSY_PRICE_XPATH).send_keys(
            int(items_to_list["Price"][i])
        )
        time.sleep(random.uniform(0.15, 0.4))
        # QUANTITY
        qty = driver.find_element_by_xpath(ETSY_QTY_XPATH).send_keys(Keys.BACKSPACE)
        qty = driver.find_element_by_xpath(ETSY_QTY_XPATH).send_keys(
            int(items_to_list["Quantity"][i])
        )
        # SHIPPING DEFAULT
        time.sleep(random.uniform(0.15, 0.4))
        ship_default = driver.find_element_by_xpath(ETSY_SHIP_XPATH).send_keys(Keys.END)
        time.sleep(random.uniform(0.15, 0.4))
        ship_default = driver.find_element_by_xpath(ETSY_SHIP_XPATH).click()
        time.sleep(random.uniform(0.15, 0.4))
        # PUBLISH
        publish = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_PUBLISH_XPATH)))
            .click()
        )
        time.sleep(random.uniform(0.15, 0.4))
        # CONFIRM
        confirm = (
            WebDriverWait(driver, 10)
            .until(EC.element_to_be_clickable((By.XPATH, ETSY_CONFIRM_XPATH)))
            .click()
        )
        time.sleep(random.randint(3, 5))
        driver.quit()
    driver.quit()
