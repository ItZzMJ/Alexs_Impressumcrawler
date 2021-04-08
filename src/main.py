import json
import os
import re
import statistics
from dotenv import load_dotenv
from time import sleep
from selenium import webdriver
import requests
from selenium.common.exceptions import WebDriverException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.wait import WebDriverWait


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
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        #options.add_argument('--allow-insecure-localhost')

        self.driver = webdriver.Chrome("/usr/bin/chromedriver", options=options)

        load_dotenv()
        self.driver.set_window_position(3000, 0)
        self.driver.maximize_window()
        self.api_url = os.getenv("API_URL")
        self.token = os.getenv("TOKEN")
        self.searched_for_alt_impressums = False
        self.debug = []

    def run(self):
        self.debug.append("Starting ImpressumCrawler")
        driver = self.driver

        data = self.get_data()
        valid_mails = dict()

        for id in data:
            self.searched_for_alt_impressums = False
            website = data[id]
            #website = "http://www.schwendi.de/home/leben%2b_%2bfreizeit/schulen.html"
            #website = "http://www.bever.de"

            website = website.replace("https://", "").replace("http://", "").strip("/")

            url = "http://" + website
            print("checking " + url)
            self.debug.append(url)
            try:
                driver.get(url)
            except WebDriverException:
                #print("WebDriverException #1 refreshing..")
                self.debug.append("WebDriverException #1 refreshing..")
                try:
                    driver.refresh()
                except WebDriverException as e:
                    #print("No Website!")
                    self.debug.append("No Website!")
                    #print(e)
                    self.debug.append(e)
                    continue
            else:
                # check if site is for sale
                if "Website steht zum Verkauf" in driver.title:
                    #print("Website is for Sale!")
                    self.debug.append("Website is for Sale!")
                    continue

                # find Impressum link
                if self.find_impressum() == -1:
                    # no Impressum found
                    #print("No impressum found! find alternative Impressum..")
                    self.debug.append("No impressum found! find alternative Impressum..")

                    if self.find_impressum_alternatives() == -1:
                        #print("No alternative Impressums found. Look on current page for email")
                        self.debug.append("No alternative Impressums found. Look on current page for email")
                        # if no impressum look on the current site for an email
                        #continue

                source = driver.page_source

                file = open("source.html", 'w')
                file.write(source)
                file.close()

                valid_mails[int(id)] = self.get_valid_mails(source, website)
                # check in frames
                if not valid_mails[int(id)]:
                    valid_mails[int(id)] = self.check_frames(website)

                # if valid mails is empty and alternate impressums wasnt searched yet
                if not valid_mails[int(id)] and not self.searched_for_alt_impressums:
                    #print("Alt impressums lief noch nicht")
                    #print(self.searched_for_alt_impressums)
                    self.debug.append("Alt impressums lief noch nicht")
                    self.debug.append(self.searched_for_alt_impressums)

                    if self.find_impressum_alternatives() == -1:
                        #print("No alternative Impressums found.")
                        self.debug.append("No alternative Impressums found.")
                    else:
                        source = driver.page_source
                        valid_mails[int(id)] = self.get_valid_mails(source, website)

                # if valid mails still empty page is maybe stuck in error page
                elif not valid_mails[int(id)]:
                    valid_mail = self.click_link_and_search_again(website)
                    if valid_mail is not None:
                        valid_mails[int(id)] = valid_mail
            sleep(10)

        self.submit_data(valid_mails)

    def get_valid_mails(self, source, website):

        p = re.compile(r"([a-zA-Z0-9_.+-]+@+[(?:a-zA-Z?)]+(?:\d|)+(?:\d|[a-zA-Z0-9-])+(?:\.|\(dot\))+[a-zA-Z0-9-.]+)")
        mails = p.findall(source)

        # if mails empty try (at) or [at] instead of @
        if not mails:
            p = re.compile(r"([a-zA-Z0-9_.+-]+(?:@|\(at\)|\[at]| @ )+[(?:a-zA-Z?)]+(?:\d|)+(?:\d|[a-zA-Z0-9-])"
                           r"+(?:\.|\(dot\))+[a-zA-Z0-9-.]+)")
            mails = p.findall(source)

        #print(mails)
        self.debug.append(mails)

        domain = website.replace("www.", "").replace("https://", "").replace("http://", "").replace("/", "")
        #print("Domain: " + domain)
        self.debug.append("Domain: " + domain)

        valid_mails = []

        # get valid mails for the domain
        for email in mails:
            if domain in email:
                valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

            # if email ends with .com instead of .de for example
            elif domain.rsplit(".", 1)[0] in email:
                valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@").replace(" @ ", "@").replace("(dot)", "."))

            # if domain is to 80% email prefix for example: www.ib-shoefer.de and IB.shoefer@t-online.de
            elif self.compare_string(domain.rsplit(".", 1)[0], email.split("@")[0]) > 0.8:
                valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

        if not valid_mails:
            #print("Valid_mails empty!")
            self.debug.append("Valid_mails empty!")

            # check if domains contains two dots like shop.corilla.de
            if re.search(r'(?<!\.)\.\.(?!\.)', domain):
                #print("domain contains two dots! splitting..")
                self.debug.append("domain contains two dots! splitting..")
                domain = domain.split(".", 1)

            for email in mails:
                if domain in email:
                    valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

                # if domain is to 80% email prefix for example: www.ib-shoefer.de and IB.shoefer@t-online.de
                elif self.compare_string(domain.rsplit(".", 1)[0], email.split("@")[0]) > 0.7:
                    valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

        if not valid_mails:
            valid_mails = mails

        # remove duplicates
        valid_mails = list(dict.fromkeys(valid_mails))
        print(valid_mails)
        return valid_mails

    def find_impressum(self):
        driver = self.driver

        try:
            impressum_links = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements_by_link_text("Impressum"))
        except TimeoutException:
            #print("No Impressum Link text")
            self.debug.append("No Impressum Link text")
        else:
            for impressum_link in impressum_links:
                #print("Found Impressum link by text:")
                self.debug.append("Found Impressum link by text:")

                link = impressum_link.get_attribute("href")
                #print(link)
                self.debug.append(link)

                # if javascript link click it
                if "javascript" in link:
                    try:
                        impressum_link.click()
                    except ElementClickInterceptedException:
                        if "javascript:void(0)" in link and impressum_link.get_attribute("onclick") is not None:
                            #print("Executing script to click")
                            self.debug.append("Executing script to click")
                            driver.execute_script(impressum_link.get_attribute("onclick"))

                        else:
                            #print("Element not clickable")
                            self.debug.append("Element not clickable")
                            # return -1
                else:
                    driver.get(link)
                sleep(2)
                return 1

        try:
            links = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements_by_tag_name("a"))
        except TimeoutException:
            #print("No links on the page!")
            self.debug.append("No links on the page!")
            return -1

        impressum_link = ""
        #print links
        for link in links:
            #print(link.get_attribute("href"))
            self.debug.append(link.get_attribute("href"))

        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue

            if "impressum" in link.get_attribute("href"):
                impressum_link = link.get_attribute("href")
                break

            elif "Impressum" in link.get_attribute("href"):
                impressum_link = link.get_attribute("href")
                break

            elif "Impressum" in link.text:
                impressum_link = link.get_attribute("href")
                break

        if impressum_link:
            driver.get(impressum_link)
            sleep(2)
            return 1
        else:
            return -1

    def find_impressum_alternatives(self):
        driver = self.driver
        self.searched_for_alt_impressums = True

        impressum_alternatives = ["IMPRESSUM", "impressum", "Disclaimer", "disclaimer", "comany-info", "legal-notice", "Kontakt",
                                  "KONTAKT", "contact"]

        for alt in impressum_alternatives:
            links = []
            try:
                impressum_links = WebDriverWait(driver, 2).until(
                    lambda driver: driver.find_elements_by_link_text(alt))
            except TimeoutException:
                #print("No " + alt +" Link text")
                self.debug.append("No " + alt +" Link text")
            else:
                for impressum_link in impressum_links:
                    #print("Found Impressum link by text: " + alt)
                    #print(impressum_link.get_attribute("href"))
                    self.debug.append("Found Impressum link by text: " + alt)
                    self.debug.append(impressum_link.get_attribute("href"))

                    driver.get(impressum_link.get_attribute("href"))
                    sleep(2)
                    return 1

            try:
                links = WebDriverWait(driver, 2).until(
                    lambda driver: driver.find_elements_by_tag_name("a"))
            except TimeoutException:
                #print("No " + alt + " links on the page!")
                self.debug.append("No " + alt + " links on the page!")
            else:
                impressum_link = ""
                # print links
                #for link in links:
                #    print(link.get_attribute("href"))

                for link in links:
                    href = link.get_attribute("href")
                    if not href:
                        continue

                    if alt.lower() in link.get_attribute("href"):
                        impressum_link = link.get_attribute("href")
                        break

                    elif alt in link.get_attribute("href"):
                        impressum_link = link.get_attribute("href")
                        break

                    elif alt in link.text:
                        impressum_link = link.get_attribute("href")
                        break

                if impressum_link:
                    driver.get(impressum_link)
                    sleep(2)
                    return 1

        frames = list()
        iframes = list()
        # if no impressum alternative is found check for frames and iframes
        try:
            frames = WebDriverWait(driver, 2).until(
                lambda driver: driver.find_elements_by_tag_name("frame"))
        except TimeoutException:
            #print("No Frames found")
            self.debug.append("No Frames found")

        try:
            iframes = WebDriverWait(driver, 2).until(
                lambda driver: driver.find_elements_by_tag_name("iframe"))
        except TimeoutException:
            #print("No iFrames found")
            self.debug.append("No iFrames found")

        frames.extend(iframes)

        if frames:
            for frame in frames:
                #print("Frame:")
                self.debug.append("Frame:")
                #try:
                frame_name = frame.get_attribute("name")
                #except
                #print(frame_name)
                self.debug.append(frame_name)

                #driver.switch_to.frame(driver.find_element_by_xpath("//frame[@src='" + frame_src + "']"))
                if frame_name:
                    driver.switch_to.frame(frame_name)
                else:
                    continue
                if self.find_impressum() == 1:
                    return 1
                else:
                    driver.switch_to.parent_frame()

        return -1

    def compare_string(self, domain, email):
        erg = []
        domain = self.delete_special_chars(domain).lower()
        email = self.delete_special_chars(email).lower()
        # print("Comparing: " + domain + " And: " + email)

        for a, b in zip(domain, email):
            if a == b:
                erg.append(1)
            else:
                erg.append(0)
        # return average (durchschnitt)
        return statistics.mean(erg)

    def delete_special_chars(self, string):
        return string.replace("-", "").replace(".", "").replace("_", "").replace(":", "").replace("+", "")

    def get_data(self):
        self.debug.append("getting data")
        url = self.api_url + "getNotVerifiedEmails"

        try:
            host = os.environ['HOSTNAME']
        except KeyError:
            data = {"token": self.token}
        else:
            data = {"token": self.token, "host": host}

        result = requests.post(url, data=data)

        if result.status_code != 200:
            #print("Fehler! Status: " + str(result.status_code))
            self.debug.append("Fehler! Status: " + str(result.status_code))
            p = re.compile("<!--(.*?)-->", re.DOTALL)
            error = p.findall(result.text)[0]

            #print(error)
            self.debug.append(error)
            return -1

        data = json.loads(result.text)
        self.debug.append("getting data complete")

        return data

    def submit_data(self, valid_mails):
        self.debug.append("submitting data")

        url = self.api_url + "storeCrawledEmails"

        try:
            host = os.environ['HOSTNAME']
        except KeyError:
            data = {"token": self.token, "data": valid_mails}
        else:
            data = {"token": self.token, "host": host, "data": valid_mails}

        data = json.dumps(data)
        #print("Submitting data:")
        #print(data)
        self.debug.append("submitting data:")
        self.debug.append(data)

        result = requests.post(url, json=data)

        if result.status_code != 200:
            #print("Fehler! Status: " + str(result.status_code))
            self.debug.append("Fehler! Status: " + str(result.status_code))
            p = re.compile("<!--(.*?)-->", re.DOTALL)
            error = p.findall(result.text)[0]
            #print(error)
            self.debug.append(error)
        else:
            self.debug.append("finished.")


    def click_link_and_search_again(self, website):
        driver = self.driver
        #print("clicking any link and try again")
        self.debug.append("clicking any link and try again")
        try:
            frames = WebDriverWait(driver, 3).until(
                lambda driver: driver.find_elements_by_tag_name("frame"))
        except TimeoutException:
            try:
                links = WebDriverWait(driver, 5).until(
                    lambda driver: driver.find_elements_by_tag_name("a"))
            except TimeoutException:
                #print("No links on the page!")
                self.debug.append("No links on the page!")
            else:
                #print(links[0].text)
                self.debug.append(links[0].text)

                if website in links[0].text:
                    links[0].click()
                    if self.find_impressum() == -1:
                        # no Impressum found
                        #print("No impressum found! find alternative Impressum..")
                        self.debug.append("No impressum found! find alternative Impressum..")
                        if self.find_impressum_alternatives() == -1:
                            #print("No alternative Impressums found. Look on current page for email")
                            self.debug.append("No alternative Impressums found. Look on current page for email")
                            return None
                            # if no impressum look on the current site for an email
                            # continue

                source = driver.page_source

                valid_mails = self.get_valid_mails(source, website)
                return valid_mails
        else:
            return None

    def check_frames(self, website):
        # print("checking frames")
        self.debug.append("checking frames")
        driver = self.driver
        # walk frames if existent and try to find email

        frames = list()
        iframes = list()

        try:
            frames = WebDriverWait(self.driver, 5).until(
                lambda driver: driver.find_elements_by_tag_name("frame"))
        except TimeoutException:
            #print("No normal Frames found")
            self.debug.append("No normal Frames found")

        try:
            iframes = WebDriverWait(self.driver, 5).until(
                lambda driver: driver.find_elements_by_tag_name("iframe"))
        except TimeoutException:
            #print("No iFrames found")
            self.debug.append("No iFrames found")

        frames.extend(iframes)

        valid_mails = []

        if frames:
            for frame in frames:
                #print("Frame:")
                self.debug.append("Frame:")
                # try:
                frame_name = frame.get_attribute("name")
                # except

                #print(frame_name)
                self.debug.append(frame_name)

                # driver.switch_to.frame(driver.find_element_by_xpath("//frame[@src='" + frame_src + "']"))
                if frame_name:
                    driver.switch_to.frame(frame_name)
                else:
                    continue
                source = driver.page_source
                valid_mails.append(self.get_valid_mails(source, website))

                driver.switch_to.default_content()
        else:
            #print("No Frames or iFrames found")
            self.debug.append("No Frames or iFrames found")

        # flatten list
        valid_mails = [item for sublist in valid_mails for item in sublist]

        # remove duplicates
        valid_mails = list(dict.fromkeys(valid_mails))

        return valid_mails

    # print debug information
    def get_debug_info(self):
        for message in self.debug:
            print(message)

    def tear_down(self):
        self.driver.quit()


x = ImpressumCrawler()
#x.run()
try:
    x.run()
finally:
    x.tear_down()
    x.get_debug_info()

