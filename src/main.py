from urllib.parse import urlparse
import csv
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import page

# Linkpage
LINK_URL = "https://www.regiotrends.de/de/verbraucher-wirtschaft/index.news.161807.aktiv-in-der-regio-gewerbevereine-und-werbegemeinschaften-in-der-regio.html"

# Should chrome be displayed?
SHOW_CHROME = True


class ImpressumCrawler:
    def __init__(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"

        options = webdriver.ChromeOptions()
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--incognito")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument("--disable-notifications")
        options.add_argument('--disable-dev-shm-usage')
        options.page_load_strategy = "eager"
        options.add_argument('--allow-insecure-localhost')

        if not SHOW_CHROME:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        else:
            options.add_argument("start-maximized")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.driver.set_page_load_timeout(10)

        self.searched_for_alt_impressums = False
        self.debug = []

    def run(self):
        driver = self.driver

        with open("Result.csv", "w+") as f:
            csv.writer(f).writerow(["Domain", "Telefon", "Email", "possible Vorstand"])

        result = dict()

        # get links from Site
        links = self.get_links()

        # go to link and find impressums
        for link in links:
            domain = self.get_domain(link)
            impressum_data = self.get_impressum_data(link)

            if impressum_data:
                result[domain] = impressum_data
                with open("Result.csv", "a+") as f:

                    data = [domain, impressum_data[0], " | ".join(impressum_data[1]), " | ".join(impressum_data[2])]
                    csv.writer(f).writerow(data)
                    # data = "\", \"".join(impressum_data)
                    # output = "\"",  domain + "\", \"" + data + "\""
                    # f.writelines(output)

        print(result)


    def get_links(self):
        driver = self.driver
        driver.get(LINK_URL)

        link_page = page.LinkPage(self.driver)

        return link_page.get_links()

    def get_domain(self, link):
        return urlparse(link).netloc.replace("www.", "")

    def get_impressum_data(self, link, second_run=False):
        link = link.replace("https://", "http://")
        print("Finding Impressum url for " + link)
        #driver = self.driver
        #print("TEST0 " + link)
        try:
            self.driver.get(link)
        except Exception as e:
            print("Exception while getting link, trying from homepage..")
            # try from the homepage
            if not second_run:
                domain = self.get_domain(link)
                link = "http://" + domain + "/"
                return self.get_impressum_data(link, True)

            print(e)
            return []

        impressum_page = page.ImpressumPage(self.driver)

        if impressum_page.find_impressum() == -1:
            print("Could not find impressum, searching for alternatives")

            if impressum_page.find_impressum_alternatives() == -1:
                print("Could not find impressum alternatives, trying from homepage...")
                # try from the homepage
                if not second_run:
                    domain = self.get_domain(link)
                    link = "http://" + domain + "/"
                    return self.get_impressum_data(link, True)
                return []

        impressum = page.Impressum(self.driver)

        tel = impressum.get_telephone()
        if tel:
            tel = tel.strip()

        email = impressum.get_email()
        vorstand = impressum.get_vorstand()

        return [tel, email, vorstand]

    def tear_down(self):
        self.driver.quit()


if __name__ == "__main__":
    x = ImpressumCrawler()
    try:
        x.run()
    finally:
        x.tear_down()
