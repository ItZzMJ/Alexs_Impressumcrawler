import re
import statistics
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchFrameException, \
    WebDriverException
from selenium.webdriver.support.wait import WebDriverWait
from time import sleep
from locator import LinkPageLocators


class BasePage(object):
    """Base class to initialize the base page that will be called from all
    pages"""
    def __init__(self, driver):
        self.driver = driver


class LinkPage(BasePage):
    def get_links(self):
        driver = self.driver

        try:
            elems = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements(*LinkPageLocators.HIER_LINK))
        except TimeoutException:
            print("Link Elements not found")

        else:
            links = []
            for elem in elems:
                href = elem.get_attribute("href")
                # print(href)
                links.append(href)

            return links


class Impressum(BasePage):
    def get_email(self, text = None):
        driver = self.driver

        if text:
            source = text
        else:
            source = driver.page_source

        website = driver.execute_script("return window.location.hostname")

        p = re.compile(r"([a-zA-Z0-9_.+-]+@+[(?:a-zA-Z?)]+(?:\d|)+(?:\d|[a-zA-Z0-9-])+(?:\.|\(dot\))+[a-zA-Z0-9-.]+)")
        mails = p.findall(source)

        # if mails empty try (at) or [at] instead of @
        if not mails:
            p = re.compile(r"([a-zA-Z0-9_.+-]+(?:@|\(at\)|\[at]| @ )+[(?:a-zA-Z?)]+(?:\d|)+(?:\d|[a-zA-Z0-9-])"
                           r"+(?:\.|\(dot\))+[a-zA-Z0-9-.]+)")
            mails = p.findall(source)

        print(mails)
        # self.debug.append(mails)

        domain = website.replace("www.", "").replace("https://", "").replace("http://", "").replace("/", "")
        print("Domain: " + domain)
        # self.debug.append("Domain: " + domain)

        valid_mails = []

        # get valid mails for the domain
        for email in mails:
            if domain in email:
                valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

            # if email ends with .com instead of .de for example
            elif domain.rsplit(".", 1)[0] in email:
                valid_mails.append(
                    email.strip('.').replace("(at)", "@").replace("[at]", "@").replace(" @ ", "@").replace("(dot)",
                                                                                                           "."))

            # if domain is to 80% email prefix for example: www.ib-shoefer.de and IB.shoefer@t-online.de
            elif self.compare_string(domain.rsplit(".", 1)[0], email.split("@")[0]) > 0.8:
                valid_mails.append(email.strip('.').replace("(at)", "@").replace("[at]", "@")
                                   .replace(" @ ", "@").replace("(dot)", "."))

        if not valid_mails:
            print("Valid_mails empty!")
            # self.debug.append("Valid_mails empty!")

            # check if domains contains two dots like shop.corilla.de
            if re.search(r'(?<!\.)\.\.(?!\.)', domain):
                print("domain contains two dots! splitting..")
                # self.debug.append("domain contains two dots! splitting..")
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
        # self.debug.append(valid_mails)
        return valid_mails

    def get_telephone(self, text=None):
        driver = self.driver

        # try to find "Telefon"
        try:
            elems = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements_by_xpath("//*[contains(text(), 'Tel.:')]"))

        except TimeoutException:
            print("No Element with 'Tel.:' found")
            #self.get_telephone_regex(text)
            try:
                elems = WebDriverWait(driver, 5).until(
                    lambda driver: driver.find_elements_by_xpath("//*[contains(text(), 'Telefon:')]"))

            except TimeoutException:
                print("No Element with 'Telefon:' found")
                try:
                    elems = WebDriverWait(driver, 5).until(
                        lambda driver: driver.find_elements_by_xpath("//*[contains(text(), 'Fon:')]"))

                except TimeoutException:
                    print("No Element with 'Fon:' found")
                    return self.get_telephone_regex(text)

        print("Element with 'Telefon' found! Extracting numbers")
        result = []
        filtered = []
        for elem in elems:
            text = elem.text
            print("TEXT:")
            print(text)

            if "\n" in text:
                for line in text.splitlines():
                    if "Tel.:" in line:
                        print("Tel found in " + line)
                        result.append(self.extract_numbers(line))
                        break

                    elif "Telefon" in line:
                        print("Telefon found in " + line)
                        result.append(self.extract_numbers(line))
                        break

                    else:
                        result.append(self.extract_numbers(line))
            else:
                result.append(self.extract_numbers(text))

            #number)
            #print("NUMBERS:")
            #print(result)
        print("filtering result")
        for number in result:
            print("checking " + number)

            if not re.search('[a-zA-Z]', number) and re.search('[\d]', number):
                filtered.append(number)

        filtered = list(sorted(filtered, key=len))
        print("BEST NUMBER: ")
        try:
            print(filtered[0])
        except IndexError:
            print(filtered)
            print(result)
            return self.get_telephone_regex(text)

        return filtered[0]

    def extract_numbers(self, text):
        tmp = filter(self.filter_for_telephone, text)
        erg = "".join(tmp)

        return erg

    def filter_for_telephone(self, char):
        #print(char, end=' ')
        allowed_chars = ["+", " ", "-", "(", ")", "/"]
        if str.isdigit(char):
            #print("digit")
            return True
        elif char in allowed_chars:
            #print("allowed")
            return True
        else:
            #print("false")
            return False

    def get_telephone_regex(self, text=None):

        print("Searching for Telefon in text")
        driver = self.driver
        if text:
            source = text
        else:
            source = self.extract_text()

        #print(source)

        p1 = re.compile(r"^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$")
        p2 = re.compile(r"(\(?([\d \-\)\–\+\/\(]+){6,}\)?([ .\-–\/]?)([\d]+))")

        result1 = p1.findall(source)
        result2 = p2.findall(source)

        result = result1 + result2

        #print(result)

        erg = list()

        for tuple in result:
            for tel in tuple:
                tel = tel.strip()
                if len(tel) < 5:
                    continue
                else:
                    erg.append(tel)

        if erg:
            #print(f"Telefon: {erg[0]}")
            return erg[0]
        else:
            print("No Telefonnumber was found")
            return ""

    def get_vorstand(self):
        print("Searching for Vorstand")
        driver = self.driver
        text = self.extract_text()
        splitted = text.split("\n")
        result = list()

        i = 0
        # check each word for Vorstand
        for line in splitted:
            try:
                if "Vorstand" in line or "Vorsitzende" in line:
                    # if line is to long
                    if len(line) > 255:
                        j = 0
                        for word in line:
                            if "Vorstand" in word or "Vorsitzende" in word:
                                print("found possible Vorstand: " + line[i] + " " + line[i + 1] + " " + line[i + 2])
                                result.append(line[i] + " " + line[i + 1] + " " + line[i + 2])

                    else:
                        print("found possible Vorstand: " + splitted[i] + " " + splitted[i + 1] + " " + splitted[i + 2])
                        result.append(splitted[i] + " " + splitted[i + 1] + " " + splitted[i + 2])
            except IndexError:
                break
            i += 1

        return result

    def extract_text(self):
        driver = self.driver
        source = driver.page_source.replace("<br>", "\n").replace("</br>", "\n")

        # with open("source.html", "w+") as f:
        #     f.write(source)

        soup = BeautifulSoup(source, features="html.parser")

        # remove all script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()

        # with open("test.txt", "w+") as f:
        #     f.write(text)

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # with open("test2.txt", "w+") as f:
        #     f.write(text)

        return text

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


class ImpressumPage(BasePage):
    def find_impressum(self):
        print("finding impressum..")
        driver = self.driver

        try:
            impressum_links = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements_by_link_text("Impressum"))
        except TimeoutException:
            print("No Impressum Link text")

        else:
            for impressum_link in impressum_links:
                print("Found Impressum link by text:")
                #self.debug.append("Found Impressum link by text:")

                link = impressum_link.get_attribute("href")
                print(link)
                # self.debug.append(link)

                # if javascript link click it
                if "javascript" in link:
                    try:
                        impressum_link.click()
                    except ElementClickInterceptedException:
                        if "javascript:void(0)" in link and impressum_link.get_attribute("onclick") is not None:
                            print("Executing script to click")
                            # self.debug.append("Executing script to click")
                            driver.execute_script(impressum_link.get_attribute("onclick"))

                        else:
                            print("Element not clickable")
                            # self.debug.append("Element not clickable")
                            # return -1
                else:
                    try:
                        driver.get(link)
                    except WebDriverException as e:
                        print("WebDriverException")
                        print(e)

                sleep(2)
                return 1

        try:
            links = WebDriverWait(driver, 5).until(
                lambda driver: driver.find_elements_by_tag_name("a"))
        except TimeoutException:
            print("No links on the page!")
            # self.debug.append("No links on the page!")
            return -1

        impressum_link = ""
        # print links
        # for link in links:
        #     #print(link.get_attribute("href"))
        #     self.debug.append(link.get_attribute("href"))

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

        impressum_alternatives = ["IMPRESSUM", "impressum", "Disclaimer", "disclaimer", "comany-info", "legal-notice",
                                  "Kontakt",
                                  "KONTAKT", "contact"]

        for alt in impressum_alternatives:
            links = []
            try:
                impressum_links = WebDriverWait(driver, 2).until(
                    lambda driver: driver.find_elements_by_link_text(alt))
            except TimeoutException:
                print("No " + alt +" Link text")
                # self.debug.append("No " + alt + " Link text")
            else:
                for impressum_link in impressum_links:
                    print("Found Impressum link by text: " + alt)
                    print(impressum_link.get_attribute("href"))
                    # self.debug.append("Found Impressum link by text: " + alt)
                    # self.debug.append(impressum_link.get_attribute("href"))

                    driver.get(impressum_link.get_attribute("href"))
                    sleep(2)
                    return 1

            try:
                links = WebDriverWait(driver, 2).until(
                    lambda driver: driver.find_elements_by_tag_name("a"))
            except TimeoutException:
                print("No " + alt + " links on the page!")
                # self.debug.append("No " + alt + " links on the page!")
            else:
                impressum_link = ""
                # print links
                # for link in links:
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
            print("No Frames found")
            # self.debug.append("No Frames found")

        try:
            iframes = WebDriverWait(driver, 2).until(
                lambda driver: driver.find_elements_by_tag_name("iframe"))
        except TimeoutException:
            print("No iFrames found")
            # self.debug.append("No iFrames found")

        frames.extend(iframes)

        if frames:
            for frame in frames:
                print("Frame:")
                # self.debug.append("Frame:")
                # try:
                frame_name = frame.get_attribute("name")
                # except
                print(frame_name)
                # self.debug.append(frame_name)

                # driver.switch_to.frame(driver.find_element_by_xpath("//frame[@src='" + frame_src + "']"))
                if frame_name:
                    try:
                        driver.switch_to.frame(frame_name)
                    except NoSuchFrameException:
                        # self.debug.append("No such Frame")
                        print("No such Frame")
                else:
                    continue
                if self.find_impressum() == 1:
                    return 1
                else:
                    driver.switch_to.parent_frame()

        return -1





