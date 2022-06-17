from selenium.webdriver.common.by import By


class LinkPageLocators(object):
    # Link Locator für die Übersichtsseite
    HIER_LINK = (By.CSS_SELECTOR, "#news > div:nth-child(2) > div > div.text > a")
