import os

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s'
)




# ============================================================================================
def get_base_dir():
    """
    Returns the absolute path of the directory where this script is located.
    """
    logging.debug("Getting base directory.")
    return os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )


from typing import Tuple
from dotenv import load_dotenv

def get_threads_account() -> Tuple[str, str] | None:
    """
    Returns the number of threads to use for processing.
    Defaults to 4 if the environment variable is not set or invalid.
    """
    logging.debug("Loading Threads account from .env file.")
    load_dotenv()
    USERNAME = os.getenv("THREADS_USERNAME")
    PASSWORD = os.getenv("THREADS_PASSWORD")
    if USERNAME and PASSWORD:
        logging.debug("Threads account found.")
        return USERNAME, PASSWORD
    else:
        logging.error("Threads account not found in .env file.")
        return None


from selenium import webdriver
def load_driver(options=None):
    """
    Loads and returns a Selenium WebDriver instance for Chrome.
    """
    logging.debug("Loading WebDriver.")
    try:
        driver = webdriver.Chrome(options=options)
        logging.debug("WebDriver loaded successfully.")
        return driver
    except Exception as e:
        logging.error(f"Error loading WebDriver: {e}")
        return None