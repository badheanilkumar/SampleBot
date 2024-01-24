from __future__ import annotations

import csv
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
import getpass

import pandas as pd
import pyautogui
import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.chrome.service import Service as ChromeService
import webdriver_manager.chrome as ChromeDriverManager
ChromeDriverManager = ChromeDriverManager.ChromeDriverManager
#from webdriver_manager.chrome import ChromeDriverManager

log = logging.getLogger(__name__)


#service = Service()
#options = webdriver.ChromeOptions()
#driver = webdriver.Chrome(service=service, options=options)
#driver = webdriver.Chrome(ChromeDriverManager().install())

def setupLogger() -> None:
    dt: str = datetime.strftime(datetime.now(), "%m_%d_%y %H_%M_%S ")

    if not os.path.isdir('./logs'):
        os.mkdir('./logs')

    # TODO need to check if there is a log dir available or not
    logging.basicConfig(filename=('./logs/' + str(dt) + 'applyJobs.log'), filemode='w',
                        format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', datefmt='./logs/%d-%b-%y %H:%M:%S')
    log.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)


class EasyApplyBot:
    setupLogger()
    # MAX_SEARCH_TIME is 10 hours by default, feel free to modify it
    MAX_SEARCH_TIME = 60 * 60

    def __init__(self,
                 username,
                 password,
                 phone_number,
                 profile_path,
                 uploads={},
                 filename='output.csv',
                 blacklist=[],
                 blackListTitles=[]) -> None:

        log.info("Welcome to Easy Apply Bot")
        dirpath: str = os.getcwd()
        log.info("current directory is : " + dirpath)
        #options = webdriver.ChromeOptions()
        # try:
        #     log.info("trying to load default profile...")
        #     ChromeOptions options = new ChromeOptions();
        #     # options.add_argument(r"--user-data-dir={}".format(profile_path))
        #     # options.add_argument(r"--no-sandbox")
        #     # options.add_argument(r"--disable-dev-shm-usage")
        #     # options.add_argument(r'--profile-directory=Person 1')
        #     # options.add_argument(r'--remote-debugging-port=9222')
        #
        # except Exception as e:
        #     log.error("Exception: {}".format(e))

        self.uploads = uploads
        self.profile_path = profile_path
        past_ids: list | None = self.get_appliedIDs(filename)
        self.appliedJobIDs: list = past_ids if past_ids != None else []
        self.filename: str = filename
        self.options = self.browser_options()
        self.browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)
        self.wait = WebDriverWait(self.browser, 30)
        self.blacklist = blacklist
        self.blackListTitles = blackListTitles
        self.start_linkedin(username, password)
        self.phone_number = phone_number

    def get_appliedIDs(self, filename) -> list | None:
        try:
            df = pd.read_csv(filename,
                             header=None,
                             names=['timestamp', 'jobID', 'job', 'company', 'attempted', 'result'],
                             lineterminator='\n',
                             encoding='utf-8')

            df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
            df = df[df['timestamp'] > (datetime.now() - timedelta(days=2))]
            jobIDs: list = list(df.jobID)
            log.info(f"{len(jobIDs)} jobIDs found")
            return jobIDs
        except Exception as e:
            log.info(str(e) + "   jobIDs could not be loaded from CSV {}".format(filename))
            return None

    def browser_options(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-extensions")
        options.add_argument(r'--remote-debugging-port=9222')
        #options.add_argument(r'--profile-directory=Person 1')

        # Disable webdriver flags or you will be easily detectable
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Load user profile
        #options.add_argument(r"--user-data-dir={}".format(self.profile_path))
        return options

    def start_linkedin(self, username, password) -> None:
        log.info("Logging in.....Please wait :)  ")
        self.browser.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        try:
            user_field = self.browser.find_element("id","username")
            pw_field = self.browser.find_element("id","password")
            login_button = self.browser.find_element("xpath",
                        '//*[@id="organic-div"]/form/div[3]/button')
            user_field.send_keys(username)
            user_field.send_keys(Keys.TAB)
            time.sleep(2)
            pw_field.send_keys(password)
            time.sleep(2)
            login_button.click()
            oneclick_auth = self.browser.find_element(by='id', value='reset-password-submit-button')
            if oneclick_auth is not None:
                log.info("additional authentication required, sleep for 15 seconds so you can do that")
                time.sleep(15)
        except TimeoutException:
            log.info("TimeoutException! Username/password field or login button not found")

    def fill_data(self) -> None:
        self.browser.set_window_size(1, 1)
        self.browser.set_window_position(2000, 2000)

    def start_apply(self, positions, locations) -> None:
        start: float = time.time()
        self.fill_data()

        

        combos: list = []
        while len(combos) < len(positions) * len(locations):
            position = positions[random.randint(0, len(positions) - 1)]
            location = locations[random.randint(0, len(locations) - 1)]
            combo: tuple = (position, location)
            if combo not in combos:
                combos.append(combo)
                log.info(f"Applying to {position}: {location}")
                location = "&location=" + location
                self.applications_loop(position, location)
            if len(combos) > 500:
                break

    # self.finish_apply() --> this does seem to cause more harm than good, since it closes the browser which we usually don't want, other conditions will stop the loop and just break out

    def applications_loop(self, position, location):

        count_application = 0
        count_job = 0
        jobs_per_page = 0
        start_time: float = time.time()

        log.info("Looking for jobs.. Please wait..")

        self.browser.set_window_position(1, 1)
        self.browser.maximize_window()
        self.browser, _ = self.next_jobs_page(position, location, jobs_per_page)
        log.info("Looking for jobs.. Please wait..")

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            try:
                log.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search")

                # sleep to make sure everything loads, add random to make us look human.
                randoTime: float = random.uniform(1.5, 2.9)
                log.debug(f"Sleeping for {round(randoTime, 1)}")
                #time.sleep(randoTime)
                self.load_page(sleep=1)

                # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom

                scrollresults = self.browser.find_element(By.CLASS_NAME,
                    "jobs-search-results-list"
                )
                # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
                for i in range(300, 3000, 100):
                    self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults)

                #time.sleep(1)

                # get job links, (the following are actually the job card objects)
                links = self.browser.find_elements("xpath",
                    '//div[@data-job-id]'
                )

                if len(links) == 0:
                    log.debug("No links found")
                    break

                IDs = []
                
                # children selector is the container of the job cards on the left
                for link in links:
                        if 'Applied' not in link.text:
                            if link.text not in self.blacklist: #checking if applied already
                                jobID = link.get_attribute("data-job-id")
                                if jobID == "search":
                                    log.debug("Job ID not found, search keyword found instead? {}".format(link.text))
                                    continue
                                else:
                                    IDs.append(int(jobID))

                # remove already applied jobs
                before: int = len(IDs)
                jobIDs: list = [x for x in IDs if x not in self.appliedJobIDs]
                after: int = len(jobIDs)

                self.apply_to_jobs(jobIDs)

                # go to new page if all jobs are done
                if count_job == len(jobIDs):
                    jobs_per_page = jobs_per_page + 25
                    count_job = 0
                    log.info("""****************************************\n\n
                    Going to next jobs page
                    ****************************************\n\n""")
                    self.avoid_lock()
                    self.browser, jobs_per_page = self.next_jobs_page(position,
                                                                    location,
                                                                    jobs_per_page)
            except Exception as e:
                print(e)
    def apply_to_jobs(self, jobIDs):
        count_job = 0
        #self.avoid_lock() #fking annoying
        for i, jobID in enumerate(jobIDs):
            count_job += 1
            self.get_job_page(jobID)

            # get easy apply button
            button = self.get_easy_apply_button()
            # word filter to skip positions not wanted

            if button is not False:
                if any(word in self.browser.title for word in blackListTitles):
                    log.info('skipping this application, a blacklisted keyword was found in the job position')
                    string_easy = "* Contains blacklisted keyword"
                    result = False
                else:
                    string_easy = "* has Easy Apply Button"
                    log.info("Clicking the EASY apply button")
                    button.click()
                    time.sleep(1)
                    self.fill_out_fields()
                    result: bool = self.send_resume()
                    count_job += 1
            else:
                log.info("The Easy apply button does not exist or I'm too stupid to find it. Please help me.")
                string_easy = "* Doesn't have Easy Apply Button"
                result = False

            # position_number: str = str(count_job + jobs_per_page)
            # log.info(f"\nPosition {position_number}:\n {self.browser.title} \n {string_easy} \n")

            self.write_to_file(button, jobID, self.browser.title, result)
        pass
    def write_to_file(self, button, jobID, browserTitle, result) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted: bool = False if button == False else True
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite: list = [timestamp, jobID, job, company, attempted, result]
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, jobID):

        job: str = 'https://www.linkedin.com/jobs/view/' + str(jobID)
        self.browser.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    def get_easy_apply_button(self):
        try:
            buttons = self.browser.find_elements("xpath",
                '//button[contains(@class, "jobs-apply-button")]'
            )
            for button in buttons:
                if "Easy Apply" in button.text:
                    EasyApplyButton = button
                else:
                    log.debug("Easy Apply button not found")
                    EasyApplyButton = False
            
        except Exception as e: 
            print("Exception:",e)
            EasyApplyButton = False

        return EasyApplyButton

    def fill_out_fields(self):
        fields = self.browser.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
        for field in fields:

            if "Mobile phone number" in field.text:
                field_input = field.find_element(By.TAG_NAME, "input")
                field_input.clear()
                field_input.send_keys(self.phone_number)

        next_button = self.browser.find_element(By.CSS_SELECTOR, "button[aria-label='Continue to next step']")
        next_button.click()
        #upload resume
        existing_resume = self.browser.find_element(By.CSS_SELECTOR, "[aria-label='Selected']")
        if existing_resume is not None:
            next_button.click()
            forms = self.browser.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
            for form in forms:
                question = form.text
                answer = self.ans_question(question)
            next_button.click()
            #answer questions
            #upload CV
            #submit

        else:
            self.send_resume()
            # next_button.click()

        return

    # def upload_resume(self):
    #     upload_button = self.browser.find_element(By.XPATH, '//span[text()="Upload resume"]')

    def send_resume(self) -> bool:
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0],
                                                  button_locator[1])) > 0

        try:
            #time.sleep(random.uniform(1.5, 2.5))
            next_locator = (By.CSS_SELECTOR,
                            "button[aria-label='Continue to next step']")
            review_locator = (By.CSS_SELECTOR,
                              "button[aria-label='Review your application']")
            submit_locator = (By.CSS_SELECTOR,
                              "button[aria-label='Submit application']")
            submit_application_locator = (By.CSS_SELECTOR,
                                          "button[aria-label='Submit application']")
            error_locator = (By.CSS_SELECTOR,
                             "p[data-test-form-element-error-message='true']")
            upload_locator = upload_locator = (By.CSS_SELECTOR, "button[aria-label='DOC, DOCX, PDF formats only (5 MB).']")
            follow_locator = (By.CSS_SELECTOR, "label[for='follow-company-checkbox']")

            submitted = False
            while True:

                # Upload Cover Letter if possible
                if is_present(upload_locator):

                    input_buttons = self.browser.find_elements(upload_locator[0],
                                                               upload_locator[1])
                    for input_button in input_buttons:
                        parent = input_button.find_element(By.XPATH, "..")
                        sibling = parent.find_element(By.XPATH, "preceding-sibling::*[1]")
                        grandparent = sibling.find_element(By.XPATH, "..")
                        for key in self.uploads.keys():
                            sibling_text = sibling.text
                            gparent_text = grandparent.text
                            if key.lower() in sibling_text.lower() or key in gparent_text.lower():
                                input_button.send_keys(self.uploads[key])

                    # input_button[0].send_keys(self.cover_letter_loctn)
                    #time.sleep(random.uniform(4.5, 6.5))

                # Click Next or submit button if possible
                button: None = None
                buttons: list = [next_locator, review_locator, follow_locator,
                           submit_locator, submit_application_locator]
                for i, button_locator in enumerate(buttons):
                    if is_present(button_locator):
                        button: None = self.wait.until(EC.element_to_be_clickable(button_locator))

                    if is_present(error_locator):
                        for element in self.browser.find_elements(error_locator[0],
                                                                  error_locator[1]):
                            text = element.text
                            #error handling for valid answer
                            if "Please enter a valid answer" in text:
                                log.debug(text)
                                answer = self.ans_question(text)
                                if answer is None:
                                    time.sleep(10)
                                    break
                                button = None
                                break
                    if button:
                        button.click()
                        #time.sleep(random.uniform(1.5, 2.5))
                        if i in (3, 4):
                            submitted = True
                        if i != 2:
                            break
                if button == None:
                    log.info("Could not complete submission")
                    break
                elif submitted:
                    log.info("Application Submitted")
                    break

            #time.sleep(random.uniform(1.5, 2.5))


        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted

    def ans_question(self, question):
        answer = None
        if "How many" in question:
            answer = 5
        elif "sponsor" in question:
            answer = "No"
        elif 'Do you' in question:
            answer = "Yes"
        elif "have you previously" in question:
            answer = "Yes"
        elif "US citizen" in question:
            answer = "Yes"
        elif "Are you willing" in question:
            answer = "Yes"
        else:
            log.debug("Not able to answer question automatically. Please provide answer")
            #open file and document unanswerable questions, appending to it
            file = open("unanswerable.txt", "a")
            answer = input(question)
            file.write(question + answer +"\n")
            file.close()
        file = open("answered.txt", "a")
        file.write(question + ": " + answer + "\n")
        file.close()
        return answer
    def load_page(self, sleep=1):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 500
            time.sleep(sleep)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page

    def avoid_lock(self) -> None:
        x, _ = pyautogui.position()
        pyautogui.moveTo(x + 200, pyautogui.position().y, duration=1.0)
        pyautogui.moveTo(x, pyautogui.position().y, duration=0.5)
        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(0.5)
        pyautogui.press('esc')

    def next_jobs_page(self, position, location, jobs_per_page):
        self.browser.get(
            # URL for jobs page
            "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=" +
            position + location + "&start=" + str(jobs_per_page))
        self.avoid_lock()
        log.info("Lock avoided.")
        self.load_page()
        return (self.browser, jobs_per_page)

    def finish_apply(self) -> None:
        self.browser.close()


if __name__ == '__main__':

    with open("config.yaml", 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert parameters['username'] is not None
    assert parameters['password'] is not None
    assert parameters['phone_number'] is not None
    if parameters['profile_path'] == '':
        log.info("No profile path provided. Using default")
        user = getpass.getuser()
        profile_path = os.path.join("C:/Users/{}/AppData/Local/Google/Chrome/User Data".format(user))
        log.info("Using profile path: {}".format(profile_path))
        parameters['profile_path'] = profile_path

    if 'uploads' in parameters.keys() and type(parameters['uploads']) == list:
        raise Exception("uploads read from the config file appear to be in list format" +
                        " while should be dict. Try removing '-' from line containing" +
                        " filename & path")

    log.info({k: parameters[k] for k in parameters.keys() if k not in ['username', 'password']})

    output_filename: list = [f for f in parameters.get('output_filename', ['output.csv']) if f != None]
    output_filename: list = output_filename[0] if len(output_filename) > 0 else 'output.csv'
    blacklist = parameters.get('blacklist', [])
    blackListTitles = parameters.get('blackListTitles', [])

    uploads = {} if parameters.get('uploads', {}) == None else parameters.get('uploads', {})
    for key in uploads.keys():
        assert uploads[key] != None

    bot = EasyApplyBot(parameters['username'],
                       parameters['password'],
                       parameters['phone_number'],
                       parameters['profile_path'],
                       uploads=uploads,
                       filename=output_filename,
                       blacklist=blacklist,
                       blackListTitles=blackListTitles
                       )

    locations: list = [l for l in parameters['locations'] if l != None]
    positions: list = [p for p in parameters['positions'] if p != None]
    bot.start_apply(positions, locations)
