import re
from time import sleep
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import references


def log_in(driver):
    while True:
        try:
            driver.find_element(by=By.XPATH, value='/html/body/div[3]/form/div/div[1]/input').send_keys(references.user)
            driver.find_element(by=By.XPATH, value='/html/body/div[3]/form/div/div[2]/input').\
                send_keys(references.password)
            driver.find_element(by=By.XPATH, value='/html/body/div[3]/form/div/div[3]/button').click()
            return

        except NoSuchElementException:
            sleep(2)
            driver.refresh()


def search_tracking(driver, tracking):
    while True:
        try:
            trkng_box = driver.find_element(by=By.NAME, value='search_tracking_number')
            trkng_box.clear()
            trkng_box.send_keys(tracking)
            trkng_box.send_keys(Keys.RETURN)
            return
        except NoSuchElementException:
            sleep(2)
            driver.refresh()


def search_by_ref(driver, reference):
    while True:
        try:
            reference_box = driver.find_element(by=By.NAME, value='search_unique_code')
            reference_box.clear()
            reference_box.send_keys(reference)
            reference_box.send_keys(Keys.RETURN)
            return
        except NoSuchElementException:
            sleep(2)
            driver.refresh()


def detect_state(driver, place):
    state = driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[2]"
                                                   "//a[contains(@class,'active')]".format(place)).text
    return state


def is_hold(driver, place):
    try:
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]"
                                               "//*[contains(text(),'HOLD REQUEST')]".format(place))
        return True
    except NoSuchElementException:
        return False


def place_as(state, driver, place):
    try:
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[2]"
                                               "//*[contains(text(),'{}')]".format(place, state)).click()
    except NoSuchElementException:
        print("Can't place as {}".format(state))


def place_nship(driver, place, nship):
    try:
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/a[1]".format(place)).click()
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/span//input".format(place)).clear()
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/span//input".format(place)).send_keys(nship)
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/span//button".format(place)).click()
    except NoSuchElementException:
        print("Can't place nship")


def has_outbound(driver, place):
    try:
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]"
                                               "//*[contains(text(),'label')]".format(place))
        return True
    except NoSuchElementException:
        return False


def find_match(driver, place, tracking):
    try:
        driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]"
                                               "//*[contains(text(),'{}')]".format(place, tracking))
        return True
    except NoSuchElementException:
        return False


def accept_alert(driver):
    sleep(0.3)
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        pass


def match_finder(search, list_to_match, container):
    n = 0
    while n + 2 < len(search):
        result = search[n] + " " + search[n + 1] + " " + search[n + 2]
        result = result.upper()
        if result in list_to_match and result not in container:
            container.append(result)
        n += 1

    n = 0
    while n + 1 < len(search):
        result = search[n] + " " + search[n + 1]
        result = result.upper()
        if result in list_to_match and result not in container:
            container.append(result)
        n += 1

    n = 0
    while n < len(search):
        result = search[n]
        result = result.upper()
        if result in list_to_match and result not in container:
            container.append(result)
        n += 1


def detect_tracking(driver, place):
    if find_match(driver, place, 'none'):
        return 'none'
    elif find_match(driver, place, 'link to amazon'):
        return 'link to amazon '

    else:
        try:
            result = driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[3]//span//child::button".format(place))\
                .get_attribute('data-clipboard-text')
            return result
        except NoSuchElementException:
            return 'No se pudo'


def write_comment(driver, place, date, method=None, inbound=None, previous_track=None, initials='IM'):
    mensaje = ''
    if method == '1':  # When inbound is None or Link to Amazon
        mensaje = f'CM - We received inbound {inbound} - {initials} {date}'

    elif method == '2':  # When inbound different to the one we received
        mensaje = (f'CM - We received inbound {inbound} Please update'
                   f' - {initials} {date}\n\n{previous_track} not received')

    elif method == '3':  # When received two different inbounds
        mensaje = f'CM - We received additional inbound. Please add entry - {initials} {date}\n\n{inbound}'

    note = driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/a[6]".format(place))
    actual_comment = note.text
    note.click()
    text_box = driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/span//textarea".format(place))

    if actual_comment == '<click>':
        pass

    elif actual_comment != '<click>':
        if re.search('\d{6}$', actual_comment):
            mensaje = f'\n{inbound}'
        else:
            mensaje = f'\n\n{mensaje}'

    text_box.send_keys(mensaje)
    driver.find_element(by=By.XPATH, value="//tbody/tr[{}]/td[4]/div/span//button".format(place)).click()


def is_alert(driver):
    try:
        premanifests = driver.find_element(by=By.CLASS_NAME, value='shipment-size-readout').text.split()[0]
        return True if premanifests == '50' else False
    except NoSuchElementException:
        return True
