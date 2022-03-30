#!/usr/bin/env python3
# encoding: utf-8

import os
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

os.environ['PATH'] += ':' + os.getcwd() + '/selenium_drivers/'
HBTN_ROOT = 'https://intranet.hbtn.io/'

class Driver():
    def __init__(self, browser, user, pwd):
        self.USER = user
        self.PWD = pwd
        self.syllabus = {}
        self.task_list = {}
        self.current_project = None
        if browser == 'firefox':
            self.driver = webdriver.Firefox()
        elif browser == 'chrome':
            self.driver = webdriver.Chrome()

    def login(self):
        self.driver.get(HBTN_ROOT + 'auth/sign_in')
        user_field = self.driver.find_element_by_id('user_login')
        password_field = self.driver.find_element_by_id('user_password')

        user_field.send_keys(self.USER)
        password_field.send_keys(self.PWD)
        self.driver.find_element_by_name('commit').click()
        self.driver.implicitly_wait(5)

    def get_all_projects(self):
        self.driver.find_element_by_xpath(
            "//ul[not(@class)]/li[@data-original-title='Projects']"
        ).click()
        self.driver.implicitly_wait(5)
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        panels = soup.find_all('div', class_='panel')
        for panel in panels:
            project_list = {}
            topic = panel.find('h4').text.strip()
            projects = panel.find_all('li', class_='list-group-item')
            project_list.update({pr.a.text.strip(): pr.a.get('href') for pr in projects})
            self.syllabus[topic] = project_list

    def get_project_tasks(self, category, project_name):
        self.current_project = (category, project_name)
        self.driver.get(HBTN_ROOT + self.syllabus[category][project_name])
        self.driver.implicitly_wait(5)

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        self.task_list = {}
        tasks = soup.find_all('div', id=re.compile('task-num.*'))
        # TODO - Extract info from task, code parts included. For later.
        for idx, task in enumerate(tasks):
            task_info = {}
            task_info['id'] = task['data-role'].strip('task')
            task_info['name'] = task.find('h3').text.strip()
            task_info['type'] = task.find('span', class_='label').text.strip()
            task_info['score'] = (task.find('span', class_='task_score_value').text.strip()
                                    + ' - '
                                    + task.find('span', class_='task_progress_value').text.strip())
            task_file_info = task.find('div', class_='list-group-item').find_all('li')
            task_info['repo'] = task_file_info[0].text[task_file_info[0].text.find(':') + 2:]
            task_info['dir'] = task_file_info[1].text[task_file_info[1].text.find(':') + 2:]
            task_info['file'] = task_file_info[2].text[task_file_info[2].text.find(':') + 2:]
            task_info['check_btn'] = self.driver.find_element_by_xpath(
                                    f"//button[@id='task-num-{idx}-check-code-btn']")
            task_info['help_btn'] = self.driver.find_element_by_xpath(
                                    f"//button[@data-task-id='{task_info['id']}' and "
                                    + "contains(@class, 'users_done_for_task')]")
            self.task_list[idx] = task_info

    def check_task(self, task_number):
        current_project_url = (HBTN_ROOT
                                + self.syllabus[self.current_project[0]][self.current_project[1]])
        if self.driver.current_url != current_project_url:
            self.driver.get(current_project_url)
            self.driver.implicitly_wait(5)

        if task_number in self.task_list:
            self.task_list[task_number]['check_btn'].click()
            self.request_correction(self.task_list[task_number]['id'])
            self.get_result(task_number)

    def check_all_tasks(self):
        current_project_url = (HBTN_ROOT
                                + self.syllabus[self.current_project[0]][self.current_project[1]])
        if self.driver.current_url != current_project_url:
            self.driver.get(current_project_url)
            self.driver.implicitly_wait(5)

        for task_info in self.task_list.values():
            task_info['check_btn'].click()
            self.request_correction(task_info['id'])
        for idx in self.task_list:
            self.get_result(idx)

    def request_correction(self, task_id):
        WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((
            By.XPATH,
            f"//button[@data-task-id='{task_id}' and "
            + "contains(@class, 'correction_request_test_send')]"
        ))).click()
        self.driver.find_element_by_xpath(
            f"//div[@id='task-test-correction-{task_id}-correction-modal']"
            + "//button[@class='close']").click()
        WebDriverWait(self.driver, 2).until(EC.visibility_of_element_located((
            By.XPATH, "//body[not(contains(@class, 'modal-open'))]"
        )))

    def get_result(self, task_num):
        result = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((
            By.XPATH,
            (f"//div[@id='task-test-correction-{self.task_list[task_num]['id']}-correction-modal']"
                + "//div[@class='result']/hr")
        )))
        result = result.find_element_by_xpath('..')

        soup = BeautifulSoup(result.get_attribute('outerHTML'), 'lxml')
        check_list = {}
        checks = soup.find_all('div', class_='check-inline')
        for check in checks:
            check_info = {}
            check_info['id'] = check.get('id')
            check_info['status'] = check.get('title')
            check_info['checked'] = bool(check_info.get('status').split()[-1] == 'success')
            check_list[check.text.strip()] = check_info
        self.task_list[task_num]['checks'] = check_list

if __name__ == '__main__':
    driver = Driver('firefox', '2917@holbertonschool.com', 'Rm01GtZow@@h')
    driver.login()
    driver.get_all_projects()
    driver.get_project_tasks(
        'Higher-level programming - Python',
        '0x01. Python - if/else, loops, functions'
    )
    driver.check_all_tasks()
    driver.check_task(20)
