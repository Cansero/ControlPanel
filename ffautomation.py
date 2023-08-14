from datetime import datetime

import gspread
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

from ff_utils import *
from win_utils import OptionSelection

options = webdriver.ChromeOptions()
options.add_argument('ignore-certificate-errors')

# 134217728 comes from subprocess.CREATE_NO_WINDOW
chrome_service = ChromeService(popen_kw={'creation_flags': 134217728})

gc = gspread.oauth(
    credentials_filename='credentials/credentials.json',
    authorized_user_filename='credentials/authorized_user.json'
)

today = datetime.today().strftime('%m/%d/%y')
month = datetime.today().strftime('%Y-%m')


def receiving(list_from_program, time_to_sleep, run_minimized=False):

    driver = webdriver.Chrome(options=options, service=chrome_service)
    if run_minimized:
        driver.minimize_window()
    driver.get(references.url)

    log_in(driver)

    holds, not_found, repeated, problems = [], [], [], []

    for tracking, nship in list_from_program:

        search_tracking(driver, tracking)

        results = len(driver.find_elements(by=By.XPATH, value="//tbody/tr"))

        if results == 0:
            not_found.append(tracking)

        alert = is_alert(driver)

        row = 1
        times_appear = 0
        while row <= results:
            if find_match(driver, row, tracking) is True:
                state = detect_state(driver, row)
                hold = is_hold(driver, row)

                place_as('Received', driver, row)
                if alert:
                    accept_alert(driver)
                place_nship(driver, row, nship)

                if hold:
                    place_as('Hold', driver, row)
                    holds.append(tracking)

                if state in ['Problems for Forwarder', 'Problems for Client']:
                    place_as(state, driver, row)
                    problems.append(tracking)

                if alert:
                    accept_alert(driver)
                times_appear += 1
                row += 1

            else:
                row += 1

        if times_appear > 1:
            repeated.append(tracking)

        sleep(time_to_sleep)

    driver.quit()
    return repeated, holds, problems, not_found


def pre_manifest(list_from_program, time_to_sleep, run_minimized=False):

    driver = webdriver.Chrome(options=options, service=chrome_service)
    if run_minimized:
        driver.minimize_window()
    driver.get(references.url)

    log_in(driver)

    state = []
    place = 0
    for outbound in list_from_program:
        place += 1
        row = 1
        search_tracking(driver, outbound)

        results = len(driver.find_elements(by=By.XPATH, value="//tbody/tr"))
        matches = len(driver.find_elements(by=By.XPATH, value="//tbody/tr/td[3]"
                                                              "//*[contains(text(),'{}')]".format(outbound)))

        if results == 0:
            state.append(f'{place}.- {outbound} - Not found')

        elif matches > 1:
            state.append(f'{place}.- {outbound} - Repeated')

        elif results and not matches:
            state.append(f'{place}.- {outbound} - HOLD')

        else:
            while row <= results:
                if find_match(driver, row, outbound) is True:
                    active_button = detect_state(driver, row)

                    if active_button not in ['Unreceived', 'Received']:
                        state.append(f'{place}.- {outbound} - {active_button}')
                    else:
                        state.append(f'{place}.- {outbound} - Pre-manifested')

                    place_as('Pre-Manifest', driver, row)
                    accept_alert(driver)

                    row += 1

                else:
                    row += 1

        sleep(time_to_sleep)

    driver.quit()
    return state


def print_label(list_from_program):

    ff_file = gc.open('FF File').sheet1.col_values(1)
    ff_file_nship = gc.open('FF File').sheet1.col_values(2)

    driver = webdriver.Chrome(options=options, service=chrome_service)
    driver.get(references.url)

    log_in(driver)

    messages = []
    place = 0
    for tracking in list_from_program:
        place += 1
        indices = []

        if tracking[0] == 'N':
            for i, label in enumerate(ff_file_nship):
                if tracking[-12:] == label[-12:]:
                    indices.append(i)
        else:
            for i, label in enumerate(ff_file):
                if tracking[-12:] == label[-12:]:
                    indices.append(i)

        if not len(indices):
            messages.append(f'{place}.- {tracking} - Not found')

        elif len(indices) > 1:
            messages.append(f'{place}.- {tracking} - Combined')

        else:
            tracking = ff_file[indices[0]][1:]

            search_tracking(driver, tracking)

            results = len(driver.find_elements(by=By.XPATH, value="//tbody/tr"))
            row = 1

            original_window = driver.current_window_handle

            while row <= results:
                if find_match(driver, row, tracking) is True:
                    if not is_hold(driver, row):
                        driver.implicitly_wait(10)
                        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]"
                                                               "//*[contains(text(),'label')]".format(row)).click()
                        for window_andle in driver.window_handles:
                            if window_andle != original_window:
                                driver.switch_to.window(window_andle)
                                break
                        driver.execute_script("window.print();")
                        sleep(2)
                        pyautogui.press('enter')
                        sleep(0.5)
                        driver.close()
                        driver.switch_to.window(original_window)
                        outbound = driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]"
                                                                          "//*[contains(@href,'canadapost.ca')]"
                                                       .format(row)).text
                        messages.append(f'{place}.- {tracking} - {outbound}')

                        driver.implicitly_wait(0)

                    else:
                        messages.append(f'{place}.- {tracking} - Hold')

                    row += 1

                else:
                    row += 1

    driver.quit()
    return messages


def codes(list_from_program):

    cells_values = []

    item_desc = gc.open("CODES FINDER CA").worksheet("MASTER").col_values(1)

    driver = webdriver.Chrome(service=chrome_service)
    for asin in list_from_program:
        matches = []
        subtitle = None
        amz_url = "https://www.amazon.ca/dp/{}?psc=1".format(asin)

        driver.get(amz_url)

        try:
            title = driver.find_element(By.ID, "productTitle").text
        except NoSuchElementException:
            break
        try:
            subtitle = driver.find_element(By.ID, "productSubtitle").text
        except NoSuchElementException:
            pass

        title = title.replace(",", " ").replace("-", " ").replace(".", " ").split()
        if subtitle:
            subtitle = subtitle.split()
            if subtitle[0].upper() == "PAPERBACK":
                matches.append("PAPERBACK BOOK")
            if subtitle[0].upper() == "HARDCOVER":
                matches.append("HARDCOVER BOOK")

        match_finder(title, item_desc, matches)

        sel = OptionSelection(labels=matches, desc=item_desc)
        sel.exec()
        cells_values.append(sel.get_selection)

    driver.quit()
    return cells_values


def problemas(list_from_program, referencias, initials=None, run_minimized=False):

    buffalo = gc.open("BUFFALO WAREHOUSE").worksheet(f'{month}')

    driver = webdriver.Chrome(options=options, service=chrome_service)
    if run_minimized:
        driver.minimize_window()
    driver.get(references.url)

    log_in(driver)

    row = 1
    messages = []
    for tracking, reference in zip(list_from_program, referencias):
        search_by_ref(driver, reference)

        try:
            results = len(driver.find_elements(by=By.XPATH, value="//tbody/tr"))
        except NoSuchElementException:
            results = False

        if not results:

            messages.append('Not found')

        elif results > 1:
            messages.append('Need assistance')

        else:
            trkng = detect_tracking(driver, row)

            if trkng in ['none', 'link to amazon ']:
                method_no = '1'

            else:
                if not buffalo.find(trkng):
                    method_no = '2'

                else:
                    method_no = '3'

            write_comment(driver, row, today, method=method_no, inbound=tracking,
                          previous_track=trkng, initials=initials)
            place_as('Problems for Client', driver, row)
            messages.append('Problem for Client')

    driver.quit()
    return messages
