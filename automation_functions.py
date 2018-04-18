#!/usr/bin/env python

import requests
from requests_oauthlib import OAuth1
import json
import logging
import logging.handlers
import datetime
from pytz import timezone
import pytz
import time
import smtplib
from email.mime.text import MIMEText
import re
import argparse
import pickle
import os
import threading
import dateutil.parser
import re

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By

import customer_account_variables
import customer_tfs_data_normalization
import glog

_USERNAME = glog.foo
_PASSWORD = glog.bar()
_AUTHOR = 'Tom Taggart, xxxxx'
utc = pytz.utc
pacific = timezone('US/Pacific')

logger = logging.getLogger('customer_automation_functions')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
#fh = logging.FileHandler(customer_account_variables.COMMON_FUNCTIONS_LOGFILE)
fh = logging.handlers.RotatingFileHandler(customer_account_variables.COMMON_FUNCTIONS_LOGFILE, maxBytes=50000000, backupCount=5)
fh.setLevel(logging.DEBUG)
eh = logging.handlers.SMTPHandler('exit.vendor.com', 'WARNING_DO_NOT_REPLY@vendor.com',
                                  ['user1@vendor.com'], 'Message from customer automation function application')
eh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
eh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)

class TACCase():
    def __init__(self, caseNumber):
        self.caseNumber = caseNumber
        
class myThread (threading.Thread):
    def __init__(self, name, case):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger('customer_automation_functions.myThread')
        self.logger.info('Creating Thread object.')
        self.name = name
        self.case = case
    def run(self):
        self.logger = logging.getLogger('customer_automation_functions.myThread.run')        
        self.formatter = logging.Formatter('%(asctime)s [%(name)s]-%(threadName) %(levelname)s: %(message)s')
        self.logger.info('Calling TAC_info_collect_worker()...')
        case = TAC_info_collect_worker(self.case)
        return case
        self.logger.info('Calling TAC_info_collect_worker() complete.')

def TAC_info_collect_worker(case):
    _start_TACCase_info_collection_timestamp = datetime.datetime.now()
    try:
        driver = webdriver.Chrome('/Users/user1/chromedriver')
        wait = WebDriverWait(driver, 15)
        #driver.implicitly_wait(15
    except Exception as e:
        logger.info('Could not create webdriver.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:    
        logger.info('Chrome Webdriver created.')
    try:
        _website_authentication_start_timestamp = datetime.datetime.now()
        logger.info('Opening www.vendor.com website...')
        driver.get("http://www.vendor.com/")
        time.sleep(5)
    except Exception as e:
        logger.info('Could not open www.vendor.com.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        logger.info('Webdriver has opened vendor website.')
    try:
        logger.info('Webdriver is attempting to authenticate user credentials into vendor.com...')    
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
        driver.find_element_by_xpath('//*[@id="actions"]/li[1]/a').click()
        driver.find_element_by_xpath('//*[@id="userInput"]').send_keys(glog.foo)
        driver.find_element_by_xpath('//*[@id="passwordInput"]').send_keys(glog.bar())
        driver.find_element_by_xpath('//*[@id="login-button"]').click()
    except Exception as e:
        logger.info('Authentication failed.  Terminating application.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        runtime(_website_authentication_start_timestamp, 'website authentication', 'Login')
        logger.info('Webdriver has authenticated successfullly.')
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
    driver.get("https://mycase.cloudapps.vendor.com/%s" % case.caseNumber)
    time.sleep(10)
    case.description = driver.find_element_by_xpath('//*[@id="caseSummaryDescription"]/div[2]').text
    logger.debug('description=%s added for TACCase=%s.' %(case.description, case.caseNumber))
    case.status = driver.find_element_by_xpath('//*[@id="status"]/div').text
    logger.debug('Status=%s added for TACCase=%s.' %(case.status, case.caseNumber))
    case.severity = driver.find_element_by_xpath('//*[@id="caseSummarySeverity"]/div[2]/span').text               
    logger.debug('Severity=%s added for TACCase=%s.' %(case.severity, case.caseNumber))
    case.created = driver.find_element_by_xpath('//*[@id="caseSummaryCreated"]/div[2]').text
    case.created = datetime.datetime.strptime(case.created, '%Y-%m-%dT%H:%M:%SZ')
    logger.debug('dateCreated=%s added for TACCase=%s.' %(case.created, case.caseNumber))
    case.updated = driver.find_element_by_xpath('//*[@id="caseSummaryUpdated"]/div[2]').text
    logger.debug('lastUpdated=%s added for TACCase=%s.' %(case.updated, case.caseNumber))
    try:
        case.DDTS = driver.find_element_by_xpath('//*[@id="caseSummaryRelatedBugs"]/div[2]/span/a').text
    except Exception as e:
        case.DDTS = False
        logger.info('No DDTS for TAC Case %s' % case.caseNumber)
        logger.debug(e)
    else:
         logger.debug('DDTS %s added for TAC Case %s' % (case.DDTS, case.caseNumber))
    try:
        case.lossOfService = driver.find_element_by_xpath('//*[@id="caseSummaryLOS"]/div[2]/span').text
    except Exception as e:
        logger.info('No Loss of Service info for TAC Case %s' % case.caseNumber)
        logger.debug(e)
    else:
        logger.debug('Loss of Service=%s added for TAC Case %s' % (case.lossOfService, case.caseNumber))
    try:
        case.serialNumber = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                         + '/div/section/div[1]/section/div/div[6]'
                                                         + '/div/div/div/section/div/div[12]/div[2]').text
    except Exception as e:
        logger.info('No Serial Number info for TAC Case %s' % case.caseNumber)
        logger.debug(e)
    else:
        logger.debug('Serial Number %s info added for TAC Case %s' % (case.serialNumber, case.caseNumber))
    try:
        case.hostname = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                     + '/div/section/div[1]/section/div/'
                                                     + 'div[6]/div/div/div/section/div/div'
                                                     + '[13]/div[2]').text
        if 'Diagnose' in case.hostname:
            noHostname = True
            case.hostname = False
    except Exception as e:
        logger.info('No Hostname info for TAC Case %s' % case.caseNumber)
        logger.debug(e)
    else:
        if case.hostname:
            logger.debug('Hostname %s info added for TAC Case %s' % (case.hostname, case.caseNumber)) 
        else:
            logger.info('No Hostname info for TAC Case %s' % case.caseNumber)    
    try:
        case.TACEngineer = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                        + '/div/section/div[1]/section/div/div'
                                                        + '[6]/div/div/div/section/div/div[17]'
                                                        + '/div[2]').text
    except Exception as e:
        logger.info('TAC engineer has not been assigned for TAC Case %s' % case.caseNumber)
        logger.debug(e)
    else:
        logger.debug('TAC engineer %s info added for TAC Case %s' % (case.TACEngineer, case.caseNumber))
    runtime(_start_TACCase_info_collection_timestamp, 'TAC Case info collection', 'Case Webpage', 1)
    driver.close()
    logger.info('Webdriver closed.')
   
        
def set_logLevel(logLevel):
    if logLevel == "WARNING":
        ch.setLevel(logging.WARNING)
    elif logLevel == "DEBUG":
        ch.setLevel(logging.DEBUG)
    elif logLevel == "INFO":
        ch.setLevel(logging.INFO)
    elif logLevel == "ERROR":
        ch.setLevel(logging.ERROR)
    else:
        ch.setLevel(logging.CRITICAL)

def check_sender(email, logLevel):
    logger = logging.getLogger('customer_automation_functions.check_sender')
    set_logLevel(logLevel)
    logger.info('Attempting to Authorize email sender...')
    logger.debug('email=%s, variable_type=%s' % (email, type(email)))
    if email.lower() in customer_account_variables.approvedDDTSEmailSenders:
        logger.info('Email sender authorized.')
        logger.debug('email=%s, variable_type=%s' % (email, type(email)))
        return True
    else:
        logger.info('Email authorization failed.')
        logger.debug('emailList=%s' % email)
        return False
    
def validate_DDTS_ID(DDTSList, logLevel):
    logger = logging.getLogger('customer_automation_functions.validate_DDTS_ID')
    set_logLevel(logLevel)
    logger.info('Attempting to validate DDTS IDs...')
    logger.debug('DDTSList=%s, variable_type=%s' % (DDTSList, type(DDTSList)))
    for (i,DDTS) in enumerate(DDTSList):
        DDTS_part1, DDTS_part2, DDTS_part3 = DDTS[0:3].upper(), DDTS[3:5].lower(), DDTS[5:10]
        DDTS_match2 = re.compile(r'[a-z]{2}')
        DDTS_part2_valid = DDTS_match2.match(DDTS_part2)
        DDTS_match3 = re.compile(r'[0-9]{5}')
        DDTS_part3_valid = DDTS_match3.match(DDTS_part3)
        logger.debug('index=%s DDTS_part1=%s, DDTS_part2=%s, DDTS_part3=%s'
                     % (i, DDTS_part1, DDTS_part2, DDTS_part3))
        if DDTS_part1.upper() == 'CSC' and DDTS_part2_valid and DDTS_part3_valid:
            DDTSList[i] = DDTS_part1.upper() + DDTS_part2.lower() + DDTS_part3
            logger.debug('index=%s VALID_DDTS=True, DDTS=%s' % (i, DDTS))
        else:
            DDTSList[i] = 'INVALID_DDTS=%s' % DDTS
            logger.debug('index=%s VALID_DDTS=False, DDTS=%s' % (i, DDTS))
    logger.info('DDTSList IDs validated.')
    logger.debug('DDTSList=%s, variable_type=%s' % (DDTSList, type(DDTSList)))
    return DDTSList

def scriptRepository_fasterbug(DDTS, logLevel):
    logger = logging.getLogger('customer_automation_functions.scriptRepository_fasterbug')
    set_logLevel(logLevel)
    logger.info('Initializing scriptRepository parameters...')
    _taskname = 'fasterbug'
    _inputs = {}
    _auth = (_USERNAME, _PASSWORD)
    _session = requests.Session()
    logger.debug('_taskname=%s, _inputs=%s' % (_taskname, _inputs))
    _inputs = {"bug_input" : DDTS}
    _payload = json.dumps({"name": _taskname, "input": _inputs})
    logger.debug('_inputs=%s, _payload=%s' % (_inputs, _payload))
    try:
        r = _session.post('https://scripts.vendor.com/auto/api/v1/jobs',
                          data=_payload, headers={'Content-type': 'application/json'},
                          allow_redirects=True, auth=_auth)
    except Exception as e:
        logger.warning('Communication with scriptRepository backend has failed.')
        logger.debug(e)
    else:
        try:
            output = r.json()
        except Exception as e:
            logger.warning('Request to scriptRepository backend has failed.')
            logger.debug(e)
            logger.debug('HTML response code=%s' % r.status_code)
        else:
            logger.info('Request to scriptRepository backend was successful.')
            logger.debug(output)
        
        DDTSDetails = {'DDTSNumber' : 'scriptRepository Failed to return information.',
                        'DDTSTitle' : 'scriptRepository Failed to return information.',
                        'product' : 'scriptRepository Failed to return information.',
                        'DDTSStatus' : 'scriptRepository Failed to return information.',
                        'integrated' : 'scriptRepository Failed to return information.',
                        'found_in_sw' : 'scriptRepository Failed to return information.',
                         }
        
        try:
            #Try to simplify product name to OS type for customer as they may not
            #have prodcut that DDTS was found in but do have same OS.
            raw_product = output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Product']
            DDTSTitle = output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Headline']
            logger.info('Calling customer_tfs_data_normalization.product()...')
            product = customer_tfs_data_normalization.product(raw_product, DDTSTitle)   
            raw_version = output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Version']
            logger.info('Calling customer_tfs_data_normalization.found_in_sw()...')
            found_in_sw = customer_tfs_data_normalization.found_in_version(raw_version)                                                         
            raw_fixed_in_releases = output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Integrated-releases']
            logger.debug('raw_fixed_in_releases set to %s.' % str(raw_fixed_in_releases))
            logger.info('Calling customer_tfs_data_normalization.fixed_in_releases()...')
            logger.debug('product=%s, raw_fixed_in_releases=%s' % (product, str(raw_fixed_in_releases)))
            fixed_in_releases = customer_tfs_data_normalization.fixed_in_releases(product, raw_fixed_in_releases)
            
            #Build DDTS detail dicitonary to send back to calling application.  This makes it easier more fields later.
            DDTSDetails = {'DDTSNumber' : output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'id'],
                           'DDTSTitle' : output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Headline'],
                           'product' : product,
                           'DDTSStatus' : output[u'data'][u'variables'][u'bug_info'][_inputs['bug_input']][u'Status'],
                           'integrated' : str(fixed_in_releases),
                           'found_in_sw' : str(found_in_sw)
                            }
        except Exception as e:
            logger.info('Could not pull DDTS details from dictionary.')
            logger.debug(e)
        else:
            logger.info('DDTS detail dictionary Created.')
            logger.debug(DDTSDetails)
        return DDTSDetails

def scriptRepository_fasterbug_releasenote_raw(DDTS, logLevel):
    logger = logging.getLogger('customer_automation_functions.scriptRepository_fasterbug_releasenote_raw')
    set_logLevel(logLevel)
    logger.info('Initializing scriptRepository parameters...')
    _taskname = 'fasterbug_releasenote_raw'
    _inputs = {}
    _auth = (_USERNAME, _PASSWORD)
    _session = requests.Session()
    logger.debug('taskname=%s, inputs=%s' % (_taskname, _inputs))
    _inputs = {"bug" : DDTS}
    _payload = json.dumps({"name": _taskname, "input": _inputs})
    r = _session.post('https://scripts.vendor.com/auto/api/v1/jobs',
                      data=_payload, headers={'Content-type': 'application/json'},
                      allow_redirects=True, auth=_auth)
    logger.debug('html response code=%s' % r.status_code)
    logger.debug(r)
    output = r.json()
    logger.debug(output)
    DDTSReleaseNote = 'scriptRepository Failed to return information.'
    DDTSReleaseNote = re.sub(r'<[/]?B>', '', output[u'data'][u'variables'][u'bug_release_note'])
    logger.info('DDTS Release Note Created.')
    logger.debug(DDTSReleaseNote)
    return DDTSReleaseNote

def get_bugTrackers_ddts_release_note(DDTS, logLevel):
    logger = logging.getLogger('customer_automation_functions.bugTrackers_rest_releasenote')
    set_logLevel(logLevel)
    logger.info('Initializing OAuth1 parameters...')
    _bugTrackerS_CONSUMER_KEY = glog.bugTrackerS_CONSUMER_KEY
    _bugTrackerS_CONSUMER_SECRET = glog.bugTrackerS_CONSUMER_SECRET
    _url = 'https://bugTrackersng.vendor.com/wsapi/LTS-5.0/api/bug/%s/note/Release-note' % DDTS
    _auth = OAuth1(_bugTrackerS_CONSUMER_KEY, _bugTrackerS_CONSUMER_SECRET)
    _r = requests.get(_url, auth=_auth)
    logger.debug('html response code=%s' % _r.status_code)
    logger.debug(_r.text)
    DDTSReleaseNote = 'bugTrackerS REST API Failed to return information.'
    if _r.text:
        DDTSReleaseNote = re.sub(r'<[/]?B>', '', _r.text)
    logger.info('DDTS Release Note Created.')
    logger.debug(DDTSReleaseNote)
    return DDTSReleaseNote


def scriptRepository_fasterbug_fixedin(DDTS, logLevel):
    _taskname = 'fasterbug_fixedin'
    _inputs = {}
    _auth = (_USERNAME, _PASSWORD)
    _session = requests.Session()
    logger.debug('_taskname=%s, _inputs=%s' % (_taskname, _inputs))
    _inputs = {"bug_input" : DDTS}
    _payload = json.dumps({"name": _taskname, "input": _inputs})
    logger.debug('_inputs=%s, _payload=%s' % (_inputs, _payload))
    try:
        r = _session.post('https://scripts.vendor.com/auto/api/v1/jobs',
                          data=_payload, headers={'Content-type': 'application/json'},
                          allow_redirects=True, auth=_auth)
    except Exception as e:
        logger.warning('Communication with scriptRepository backend has failed.')
        logger.debug(e)
    else:
        try:
            output = r.json()
        except Exception as e:
            logger.warning('Request to scriptRepository backend has failed.')
            logger.debug(e)
            logger.debug('HTML response code=%s' % r.status_code)
        else:
            logger.info('Request to scriptRepository backend was successful.')
            logger.debug(output)
        DDTSDetails = {
                       'integrated' : output[u'data'][ u'variables'][ u'bug_fixed_in'][DDTS][ u'fixed_in'],
        }   
        return DDTSDetails

def scriptRepository_borgv3_bug_api(DDTS, logLevel):
    output2 = 'Error occured requesting information from scriptRepository.'
    _taskname = 'borgv3_bug_api'
    _inputs = {}
    _auth = (_USERNAME, _PASSWORD)
    _session = requests.Session()
    logger.debug('_taskname=%s, _inputs=%s' % (_taskname, _inputs))
    _inputs = {"bug" : DDTS, 'query': 'details'}
    _payload = json.dumps({"name": _taskname, "input": _inputs})
    logger.debug('_inputs=%s, _payload=%s' % (_inputs, _payload))
    try:
        r = _session.post('https://scripts.vendor.com/auto/api/v1/jobs',
                          data=_payload, headers={'Content-type': 'application/json'},
                          allow_redirects=True, auth=_auth)
    except Exception as e:
        logger.warning('Communication with scriptRepository backend has failed.')
        logger.debug(e)
    else:
        try:
            output = r.json()
        except Exception as e:
            logger.warning('Request to scriptRepository backend has failed.')
            logger.debug(e)
            logger.debug('HTML response code=%s' % r.status_code)
        else:
            logger.info('Request to scriptRepository backend was successful.')
            logger.debug(output)
        try:
            output2 = str(output[u'data'][u'variables'][DDTS][u'Integrated-releases']).strip('[]')
            pattern1 = re.compile('u\'')
            pattern2 = re.compile('\'')
            output2 = re.sub(pattern1, '', output2)
            output2 = re.sub(pattern2, '', output2)
        except Exception as e:
            logger.debug('Response from scriptRepository was malformed.')
            logger.debug(e)
        DDTSDetails = {
                       'integrated' : 'Integrated in: ' + output2,
                       'DDTSNumber' : output[u'data'][u'variables'][DDTS][u'id'],
                       'DDTSTitle' : output[u'data'][u'variables'][DDTS][u'Headline'],
                       'product' : output[u'data'][u'variables'][DDTS][u'Product'],
                       'DDTSStatus' : output[u'data'][u'variables'][DDTS][u'Status'],
        }
        return DDTSDetails

def purge_DDTS_email(DDTS, logLevel):
    logger = logging.getLogger('customer_automation_functions.purge_DDTS_email')
    set_logLevel(logLevel)
    logger.info('Attempting to create and end purge email to user1@vendor.com')
    purgeMSG = MIMEText('PURGE_DRAFTS_FOLDER')
    purgeMSG['Subject'] = 'PURGE_DRAFTS_FOLDER_DDTS=%s' % DDTS
    purgeMSG['To'] = 'user1@vendor.com' 
    try:
        s = smtplib.SMTP('exit.vendor.com:25')
        s.sendmail('user1@vendor.com', 'user1@vendor.com', purgeMSG.as_string())
    except Exception as e:
        logger.warning('Outbound SMTP connection has failed for exit.vendor.com:25')
        logger.debug(e)
    else:
        logger.info('DDTS_PURGE email sent to user1@vendor.com...')
    finally:
        s.quit()

def runtime(_startTimeStamp, _entity, _units, _divisor=1):
    logger = logging.getLogger('customer_automation_functions.runtime')
    _endTimeStamp = datetime.datetime.now()
    _runtime = _endTimeStamp - _startTimeStamp
    logger.info('It took %s %s to complete.' % (_entity, _runtime))
    if _divisor >1:
        logger.info('Average time for %i %s(s) was %s.' % (_divisor, _units, (_runtime/_divisor)))
    return _runtime


def get_TACCase_objects_selenium(logLevel, _status='only_open', _return_filter=None): 
    _function_start_timestamp = datetime.datetime.now()
    logger = logging.getLogger('customer_automation_functions.get_TACCase_objects_selenium')
    logger.info('Creating Selenium Chrome webdriver...')
    try:
        options = webdriver.ChromeOptions()
        #options.add_argument("--kiosk")
        driver = webdriver.Chrome('/Users/user1/chromedriver', chrome_options=options)
        driver.maximize_window()
        wait = WebDriverWait(driver, 15)
    except Exception as e:
        logger.info('Could not create webdriver.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:    
        logger.info('Chrome Webdriver created.')
    try:
        _website_authentication_start_timestamp = datetime.datetime.now()
        logger.info('Opening www.vendor.com website...')
        driver.get("http://www.vendor.com/")
    except Exception as e:
        logger.info('Could not open www.vendor.com.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        logger.info('Webdriver has opened vendor website.')
    try:
        logger.info('Webdriver is attempting to authenticate user credentials into vendor.com...')    
        time.sleep(5)
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
        driver.find_element_by_xpath('//*[@id="actions"]/li[1]/a').click()
        driver.find_element_by_xpath('//*[@id="userInput"]').send_keys(glog.foo)
        driver.find_element_by_xpath('//*[@id="passwordInput"]').send_keys(glog.bar())
        driver.find_element_by_xpath('//*[@id="login-button"]').click()
    except Exception as e:
        logger.info('Authentication failed.  Terminating application.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        runtime(_website_authentication_start_timestamp, 'website authentication', 'Login')
        logger.info('Webdriver has authenticated successfullly.')
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
    
    _collect_TACCase_numbers_start_timestamp =  datetime.datetime.now()
    caseList = []
    iteration = 0
    for key in customer_account_variables.CONTRACT_NUMBERS:
        iteration +=1
        driver.get("https://mycase.cloudapps.vendor.com/case")
        time.sleep(5)
        try:    
            logger.info('Selecting show advanced filters link...')
            time.sleep(5)
            #deselect draft cases
            driver.find_element_by_xpath('//*[@id="D"]').click()
            '''
            #27-Feb-2017 Removed due to CCO website change.
            driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]/section/div[2]'
                                         + '/section/div[1]/form/div/div[2]/a/span[3]').click()
            '''
            driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]/'
                                         + 'section/div[2]/section/div[1]/form/div/div/div[13]/'
                                         + 'a/span[1]/span').click()
            
        except Exception as e:
            logger.debug('Timed out trying to select show advanced filters link.')
            logger.debug(e)
        else:
            logger.info('Success selecting show advanced filters link.')
        try:    
            logger.info('Webdriver is attempting to find last 30 days of '
                        + 'TAC cases for specified contract...')
            if _status == 'all':
                driver.find_element_by_xpath('//*[@id="C"]').click()
            elif _status == 'only_closed':
                driver.find_element_by_xpath('//*[@id="C"]').click() #closed
                driver.find_element_by_xpath('//*[@id="O"]').click() #open
            elif _status == 'only_open':
                pass
            else:
                logger.info('Status argument passed into function is not supported.  '
                            + 'Generating dictionary for both open and closed cases.')
                logger.debug('argument=%s not supported by function.' % status)
        except Exception as e:
            logger.info('Could no fill out advanced filters form.')
            logger.debug(e)
        else:
            logger.info('Correctly filled out advanced filter form.')
        
        driver.find_element_by_xpath('//*[@id="filterContract"]').send_keys(key)
        '''
        #Removed 27-Feb-2017 due to CCO website change
        driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]'
                                     + '/section/div[2]/section/div[1]/form/div/div[2]/button').click()
        '''
        driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]'
                                     + '/section/div[2]/section/div[1]/form/div/div/div[13]'
                                     + '/button/span').click()
        
        try:
            time.sleep(8)
            caseList += driver.find_elements_by_xpath('//*[@id="framework-content-main"]/div'
                                                      + '/section/div[1]/section/div[2]/section/div[3]'
                                                      + '/div/div[2]/table/tbody//a')
        except Exception as e:
            logger.info('Webdriver could not open up TAC case list.  Terminating application.')
            logger.debug('contractNumber=%s' % key)
            logger.debug(e)
        else:
            logger.info('Webdriver has opened case list.')
            for (index,case) in enumerate(caseList):
                logger.debug('listPosition=%s, Text=%s' % (index, case.text))
        runtime(_collect_TACCase_numbers_start_timestamp, 'TAC Case collection', 'Contract Number', iteration)
    
    TACCaseDict = {}
    pattern = re.compile(r'[0123456789]{9}')
    
    logger.info('Iterating through case data to create OBJ and OBJ.title literals...')
    logger.debug(caseList)
    for case in caseList:
        try:
            logger.info('Attempting to create regular expression pattern match to identify TAC case number...')
            logger.debug('searchedString=%s' % case.text)
            caseNumber = pattern.match(case.text)
        except Exception as e:
            logger.info('RE pattern match has errored out.')
            logger.debug(e)
        else:
            logger.info('RE pattern successfully searched.')
            if caseNumber:
                currentCaseNumber = case.text
                logger.debug(caseNumber.group(0))
                logger.debug('currentCaseNumber=%s' % currentCaseNumber)
        if caseNumber:   
            TACCaseDict[case.text] = TACCase(case.text)
        else:
            if case.text != '':
                TACCaseDict[currentCaseNumber].caseTitle = case.text
        caseNumber = None
    
    
    _start_TACCase_info_collection_timestamp = datetime.datetime.utcnow()
    iteration = 0
    for case in TACCaseDict:
        iteration += 1
        driver.get("https://mycase.cloudapps.vendor.com/%s" % TACCaseDict[case].caseNumber)
        time.sleep(10)
        TACCaseDict[case].description = driver.find_element_by_xpath('//*[@id="caseSummaryDescription"]/div[2]').text
        logger.debug('description=%s added for TACCase=%s.' %(TACCaseDict[case].description, TACCaseDict[case].caseNumber))
        TACCaseDict[case].status = driver.find_element_by_xpath('//*[@id="status"]/div').text
        logger.debug('Status=%s added for TACCase=%s.' %(TACCaseDict[case].status, TACCaseDict[case].caseNumber))
        TACCaseDict[case].severity = driver.find_element_by_xpath('//*[@id="caseSummarySeverity"]/div[2]/span').text               
        logger.debug('Severity=%s added for TACCase=%s.' %(TACCaseDict[case].severity, TACCaseDict[case].caseNumber))
        TACCaseDict[case].created = driver.find_element_by_xpath('//*[@id="caseSummaryCreated"]/div[2]').text
        #TACCaseDict[case].created = datetime.datetime.strptime(TACCaseDict[case].created, '%Y-%m-%dT%H:%M:%SZ')
        TACCaseDict[case].created = dateutil.parser.parse(TACCaseDict[case].created)
        TACCaseDict[case].created = pacific.localize(TACCaseDict[case].created)
        #TACCaseDict[case].created = TACCaseDict[case].created.replace(tzinfo=timezone('UTC')) #removed 22-Jan-2017
        logger.debug('dateCreated=%s added for TACCase=%s.' %(TACCaseDict[case].created, TACCaseDict[case].caseNumber))
        TACCaseDict[case].updated = driver.find_element_by_xpath('//*[@id="caseSummaryUpdated"]/div[2]').text
        logger.debug('lastUpdated=%s added for TACCase=%s.' %(TACCaseDict[case].updated, TACCaseDict[case].caseNumber))
        try:
            TACCaseDict[case].DDTS = driver.find_element_by_xpath('//*[@id="caseSummaryRelatedBugs"]/div[2]/span/a').text
        except Exception as e:
            TACCaseDict[case].DDTS = False
            logger.info('No DDTS for TAC Case %s' % TACCaseDict[case].caseNumber)
            logger.debug(e)
        else:
             logger.debug('DDTS %s added for TAC Case %s' % (TACCaseDict[case].DDTS, TACCaseDict[case].caseNumber))
        try:
            TACCaseDict[case].lossOfService = driver.find_element_by_xpath('//*[@id="caseSummaryLOS"]/div[2]/span').text
        except Exception as e:
            logger.info('No Loss of Service info for TAC Case %s' % TACCaseDict[case].caseNumber)
            logger.debug(e)
        else:
            logger.debug('Loss of Service=%s added for TAC Case %s' % (TACCaseDict[case].lossOfService, TACCaseDict[case].caseNumber))
        try:
            TACCaseDict[case].serialNumber = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                                          + '/div/section/div[1]/section/div/div[6]'
                                                                          + '/div/div/div/section/div/div[12]/div[2]').text
        except Exception as e:
            logger.info('No Serial Number info for TAC Case %s' % TACCaseDict[case].caseNumber)
            logger.debug(e)
        else:
            logger.debug('Serial Number %s info added for TAC Case %s' % (TACCaseDict[case].serialNumber, TACCaseDict[case].caseNumber))
        
        #Try to find the bloody hostname
        #Fist look into hostname field in TAC case
        try:    
            TACCaseDict[case].hostname = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                            + '/div/section/div[1]/section/div/'
                                                            + 'div[6]/div/div/div/section/div/div'
                                                            + '[13]/div[2]').text
        except Exception as e:
            logger.info('No hostname in TAC case field.  Setting Hostname to false.')
            logger.debug(e)
            TACCaseDict[case].hostname = False
        else:
            TACCaseDict[case].hostname = TACCaseDict[case].hostname.lower()
            logger.debug('Hostname in TAC case hostname field=%s' % TACCaseDict[case].hostname)
        #Now Validate if hostname is a good hostname
        logger.info('Validating if hostname=%s is valid...' % TACCaseDict[case].hostname)
        TACCaseDict[case].hostname = customer_tfs_data_normalization.validate_node_name(TACCaseDict[case].hostname)
        if TACCaseDict[case].hostname:
            logger.info('Hostname found in hostname field.  hostname=%s' % TACCaseDict[case].hostname)
        else:  #hostname cannot be derived from hostname field.  We now will check title and description fields
            try:
                logger.info('Hostname not in hostname field.  Parsing TAC case title name...')
                logger.info('tac case title=%s' % TACCaseDict[case].caseTitle)        
                TACCaseDict[case].hostname = customer_tfs_data_normalization.validate_node_name(TACCaseDict[case].caseTitle)            
            except Exception as e:
                logger.info('Hostname validation in title failed.')
                logger.debug(e)
            else:    
                if TACCaseDict[case].hostname:
                    logger.info('Hostname found in title field.  hostname=%s' % TACCaseDict[case].hostname)
            if not TACCaseDict[case].hostname:
                try:
                    logger.info('Hostname not in hostname or title field.  Parsing TAC case description field...')
                    logger.info('tac case description=%s' % TACCaseDict[case].description)        
                    TACCaseDict[case].hostname = customer_tfs_data_normalization.validate_node_name(TACCaseDict[case].description)            
                except Exception as e:
                    logger.info('Hostname validation in description failed.')
                    logger.debug(e)
                else:    
                    if TACCaseDict[case].hostname:
                        logger.info('Hostname found in description field.  hostname=%s' % TACCaseDict[case].hostname)
        #Check again to see if we have a hostname, if not, all has failed and we'll try to search the HTML tac case page for info
        if not TACCaseDict[case].hostname:    
            try:
                logger.info('Hostname not in hostname, title, or description field.  Parsing HTML TAC case notes page...')
                TACCaseDict[case].hostname = customer_tfs_data_normalization.node_name(TACCaseDict[case].caseNumber)
            except Exception as e:
                logger.info('Search for hostname has errored in HTML notes page search for TAC Case %s' % TACCaseDict[case].caseNumber)
                logger.debug(e)
            else:
                if TACCaseDict[case].hostname:
                    logger.debug('Hostname %s info added for TAC Case %s' % (TACCaseDict[case].hostname, TACCaseDict[case].caseNumber)) 
        if TACCaseDict[case].hostname == 'TBD':
            logger.info('No Hostname info for TAC Case %s at this time.' % TACCaseDict[case].caseNumber)    
            

        try:
            TACCaseDict[case].TACEngineer = driver.find_element_by_xpath('//*[@id="framework-content-main"]'
                                                                         + '/div/section/div[1]/section/div/div'
                                                                         + '[6]/div/div/div/section/div/div[17]'
                                                                         + '/div[2]').text
        except Exception as e:
            logger.info('TAC engineer has not been assigned for TAC Case %s' % TACCaseDict[case].caseNumber)
            logger.debug(e)
        else:
            logger.debug('TAC engineer %s info added for TAC Case %s' % (TACCaseDict[case].TACEngineer, TACCaseDict[case].caseNumber))
        
    runtime(_start_TACCase_info_collection_timestamp, 'TAC Case info collection', 'Case Webpage', iteration)
    driver.close()
    logger.info('Webdriver closed.')
    
    if _return_filter == 's1':
        s1_TACCaseDict = {}
        logger.info('Building Dict for s1 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] == 'S1':
                s1_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s1_TACCaseDict
    elif _return_filter == 's2':
        s2_TACCaseDict = {}
        logger.info('Building Dict for s2 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] == 'S2':
                s2_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s2_TACCaseDict
    elif _return_filter == 's1s2':
        s1s2_TACCaseDict = {}
        logger.info('Building Dict for s1s2 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] in ('S1', 'S2'):
                s1s2_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s1s2_TACCaseDict
    elif _return_filter == 'lastX':
        lastX_TACCaseDict = {}
        _dateTime = datetime.datetime.now()
        _10MinutesAgo = _dateTime - datetime.timedelta(minutes=10)
        logger.info('Building Dict for last10 minutes cases...')
        for key in TACCaseDict:
            if _10MinutesAgo <= TACCaseDict[key].created <= _time.now:
                last1X_TACCaseDict[key] = TACCaseDict[key]
            else:
                pass
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return lastX_TACCaseDict
    elif _return_filter == 'DDTS':
        DDTS_TACCaseDict = {}
        logger.info('Building Dict for cases with DDTS...')
        for key in TACCaseDict:
            if TACCaseDict[key].DDTS:
                DDTS_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return DDTS_TACCaseDict    
    else:
        logger.info('Returning unfiltered TAC cases...')
        runtime(_function_start_timestamp, 'get_TACCase_objects_selenium', 'TAC Case', len(TACCaseDict))
        return TACCaseDict


def get_TACCase_objects_selenium_threading(logLevel, _status='only_open', _return_filter=None): 
    _function_start_timestamp = datetime.datetime.now()
    logger = logging.getLogger('customer_automation_functions.get_TACCase_objects_selenium_threading')
    logger.info('Creating Selenium Chrome webdriver...')
    try:
        driver = webdriver.Chrome('/Users/user1/chromedriver')
        wait = WebDriverWait(driver, 15)
        #driver.implicitly_wait(15)
    except Exception as e:
        logger.info('Could not create webdriver.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:    
        logger.info('Chrome Webdriver created.')
    try:
        _website_authentication_start_timestamp = datetime.datetime.now()
        logger.info('Opening www.vendor.com website...')
        driver.get("http://www.vendor.com/")
    except Exception as e:
        logger.info('Could not open www.vendor.com.  Terminating program.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        logger.info('Webdriver has opened vendor website.')
    try:
        logger.info('Webdriver is attempting to authenticate user credentials into vendor.com...')    
        time.sleep(5)
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
        driver.find_element_by_xpath('//*[@id="actions"]/li[1]/a').click()
        driver.find_element_by_xpath('//*[@id="userInput"]').send_keys(glog.foo)
        driver.find_element_by_xpath('//*[@id="passwordInput"]').send_keys(glog.bar())
        driver.find_element_by_xpath('//*[@id="login-button"]').click()
    except Exception as e:
        logger.info('Authentication failed.  Terminating application.')
        logger.debug(e)
        os.sys.exit(1)
    else:
        runtime(_website_authentication_start_timestamp, 'website authentication', 'Login')
        logger.info('Webdriver has authenticated successfullly.')
        logger.debug('user=%s, password=%s' % (glog.foo, glog.bar))
    
    _collect_TACCase_numbers_start_timestamp =  datetime.datetime.now()
    caseList = []
    iteration = 0
    for key in customer_account_variables.CONTRACT_NUMBERS:
        iteration +=1
        driver.get("https://mycase.cloudapps.vendor.com/case")
        time.sleep(5)
        try:    
            logger.info('Selecting show advanced filters link...')
            time.sleep(5)
            driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]/section/div[2]'
                                         + '/section/div[1]/form/div/div[2]/a/span[3]').click()
            #deselect draft cases
            driver.find_element_by_xpath('//*[@id="D"]').click()
        except Exception as e:
            logger.debug('Timed out trying to select show advanced filters link.')
            logger.debug(e)
        else:
            logger.info('Success selecting show advanced filters link.')
        try:    
            logger.info('Webdriver is attempting to find last 30 days of open and closed '
                        + 'TAC cases for specified contract...')
            if _status == 'all':
                driver.find_element_by_xpath('//*[@id="C"]').click()
            elif _status == 'only_closed':
                driver.find_element_by_xpath('//*[@id="C"]').click() #closed
                driver.find_element_by_xpath('//*[@id="O"]').click() #open
            elif _status == 'only_open':
                pass
            else:
                logger.info('Status argument passed into function is not supported.  '
                            + 'Generating dictionary for both open and closed cases.')
                logger.debug('argument=%s not supported by function.' % status)
        except Exception as e:
            logger.info('Could no fill out advanced filters form.')
            logger.debug(e)
        else:
            logger.info('Correctly filled out advanced filter form.')
        
        driver.find_element_by_xpath('//*[@id="filterContract"]').send_keys(key)
        driver.find_element_by_xpath('//*[@id="framework-content-main"]/div/section/div[1]'
                                     + '/section/div[2]/section/div[1]/form/div/div[2]/button').click()
        try:
            time.sleep(8)
            caseList += driver.find_elements_by_xpath('//*[@id="framework-content-main"]/div'
                                                      + '/section/div[1]/section/div[2]/section/div[3]'
                                                      + '/div/div[2]/table/tbody//a')
        except Exception as e:
            logger.info('Webdriver could not open up TAC case list.  Terminating application.')
            logger.debug('contractNumber=%s' % key)
            logger.debug(e)
        else:
            logger.info('Webdriver has opened case list.')
            for (index,case) in enumerate(caseList):
                logger.debug('listPosition=%s, Text=%s' % (index, case.text))
        runtime(_collect_TACCase_numbers_start_timestamp, 'TAC Case collection', 'Contract Number', iteration)
    
    TACCaseDict = {}
    pattern = re.compile(r'[0123456789]{9}')
    
    logger.info('Iterating through case data to create OBJ and OBJ.title literals...')
    logger.debug(caseList)
    for case in caseList:
        try:
            logger.info('Attempting to create regular expression pattern match to identify TAC case number...')
            logger.debug('searchedString=%s' % case.text)
            caseNumber = pattern.match(case.text)
        except Exception as e:
            logger.info('RE pattern match has errored out.')
            logger.debug(e)
        else:
            logger.info('RE pattern successfully searched.')
            if caseNumber:
                currentCaseNumber = case.text
                logger.debug(caseNumber.group(0))
                logger.debug('currentCaseNumber=%s' % currentCaseNumber)
        if caseNumber:   
            TACCaseDict[case.text] = TACCase(case.text)
        else:
            TACCaseDict[currentCaseNumber].caseTitle = case.text
        caseNumber = None
    
###<===========================start threading?
    threads = []
    logger.info('Creating thread for each TAC case...')
    for (i,case) in enumerate(TACCaseDict):
        threads.append(myThread('thread-%i:%s' % (i, TACCaseDict[case].caseNumber), TACCaseDict[case]))
        logger.debug('thread-%i:%s created.' % (i, TACCaseDict[case].caseNumber))
    num_of_threads = len(threads)
    index = 0
    current_threads = []
    while index < num_of_threads:
        if index != 0 and index % 10 == 0:
            for _threads in current_threads:
                _threads.join()
            current_threads = []    
        threads[index].start()
        current_threads.append(threads[index])
        time.sleep(5)
        index += 1
    for _threads in current_threads:
        _threads.join()    
#####<==================== End threading?

    if _return_filter == 's1':
        s1_TACCaseDict = {}
        logger.info('Building Dict for s1 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] == 'S1':
                s1_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s1_TACCaseDict
    elif _return_filter == 's2':
        s2_TACCaseDict = {}
        logger.info('Building Dict for s2 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] == 'S2':
                s2_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s2_TACCaseDict
    elif _return_filter == 's1s2':
        s1s2_TACCaseDict = {}
        logger.info('Building Dict for s1s2 cases...')
        for key in TACCaseDict:
            if TACCaseDict[key].severity[0:2] in ('S1', 'S2'):
                s1s2_TACCaseDict[key] = TACCaseDict[key]
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return s1s2_TACCaseDict
    elif _return_filter == 'lastX':
        lastX_TACCaseDict = {}
        _dateTime = datetime.datetime.now()
        _10MinutesAgo = _dateTime - datetime.timedelta(minutes=10)
        logger.info('Building Dict for last10 minutes cases...')
        for key in TACCaseDict:
            if _10MinutesAgo <= TACCaseDict[key].created <= _time.now:
                last1X_TACCaseDict[key] = TACCaseDict[key]
            else:
                pass
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return lastX_TACCaseDict
    elif _return_filter == 'DDTS':
        DDTS_TACCaseDict = {}
        logger.info('Building Dict for cases with DDTS...')
        for key in TACCaseDict:
            try:
                if TACCaseDict[key].DDTS:
                    DDTS_TACCaseDict[key] = TACCaseDict[key]
            except Exception as e:
                logger.info('TAC case %s has no DDTS.' % TACCaseDict[key].caseNumber)
            else:
                logger.debug('Added TAC Case %s to DDTS_TACCaseDict' % TACCaseDict[key].caseNumber)
        runtime(_function_start_timestamp, 'entireScript', 'TAC Case', len(TACCaseDict))
        return DDTS_TACCaseDict    
    else:
        logger.info('Returning unfiltered TAC cases...')
        runtime(_function_start_timestamp, 'get_TACCase_objects_selenium', 'TAC Case', len(TACCaseDict))
        return TACCaseDict


def in_tfs_request_queue(bug):
    logger = logging.getLogger('customer_automation_functions.in_tfs_queue')
    logger.info('Checking to see if DDTS add request has already been sent to the TFS system.')
    try:
        f = open(customer_account_variables.TFS_ADD_REQUEST_QUEUE_FILE, 'rb')
    except:
        logger.info('Could not open tfs_add_request_queue.pkl.')
        logger.debug(e)
    else:
        logger.info('Opened tfs_add_request_queue.pkl.')
    try:
        tfs_request_queue = pickle.load(f)
    except Exception as e:
        logger.info('Could not create dictionary from tfs_add_request_queue.pkl.')
        logger.debug(e)
    else:    
        logger.info('Created dictionary from tfs_add_request_queue.pkl.')
        f.close()
    if tfs_request_queue.has_key(bug):
        response = {'inQueue': True, 'addedToQueue': tfs_request_queue[bug]['request_date']}
        logger.info('DDTS %s was added to tfs_add_request_queue on %s by %s.'
                    % (bug, tfs_request_queue[bug]['request_date'],
                       tfs_request_queue[bug]['requester']))
        return response
    else:
        response = {'inQueue': False}
        logger.info('DDTS %s was not in tfs_add_request_queue.' % bug)
        return response


def find_webex_url(caseNumber):
    logger = logging.getLogger('customer_automation_functions.find_webex_url')
    logger.info('Searching for initial Webex URL for TAC case %s...' % caseNumber)
    initialWebexFound = False
    response = False
    i = 0
    while initialWebexFound == False:
        if i == 60:
            logger.info('Script has reached its timeout after trying to find Webex info for 1 hour.  Aborting program.')
            os.sys.exit(1)
        logger.info('Collecting casekwery webpage...')
        r = requests.get('http://www-tac.vendor.com/Teams/ks/c3/casekwery.php?Case=%s' % caseNumber, auth=(glog.foo, glog.bar()))
        logger.info('Recieved casekwery webpage.')
        webexURLStart = r.text.find('https://vendor.webex.com')
        logger.debug('webexURLStart=%i' % webexURLStart)
        if webexURLStart != -1:
            webexURLEnd = r.text[webexURLStart:].find("'")
            webexURLEnd += webexURLStart
            webexURL = r.text[webexURLStart: webexURLEnd]
            try:
                int(webexURL[-9:])
                webexID = webexURL[-9:]
            except Exception as e:
                webexID = "NA"
                pass
            else:
                pass
            response = {'url': webexURL, 'id': webexID}
            initialWebexFound = True
        else:
            time.sleep(120)
        i += 1
    logger.debug('returning %s' % response)
    return response


def find_sensitive_verbiage(caseNumber, verbiage):
    logger = logging.getLogger('customer_automation_functions.find_sensitive_verbiage')
    logger.info('Searching for sensitive verbiage for TAC case %s...' % caseNumber)
    verbiageFound = False  
    logger.info('Collecting casekwery webpage...')
    r = requests.get('http://www-tac.vendor.com/Teams/ks/c3/casekwery.php?Case=%s' % caseNumber, auth=(glog.foo, glog.bar()))
    logger.info('Recieved casekwery webpage.')
    logger.info('Checking for verbiage=%s' % verbiage)
    verbiageCount = r.text.lower().count(verbiage)
    logger.debug('verbiageCount=%i' % verbiageCount)
    if verbiageCount > 0:
        verbiageFound = True
    else:
        pass
    logger.debug('verbiage=%s, verbiageFound=%s' % (verbiage, verbiageFound))
    return verbiageFound




if __name__ == '__main__':
    _start_script_timestamp = datetime.datetime.now()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--loggingLevel",
                        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                        default='WARNING', help="Enable console logging level.")
    args = parser.parse_args()
    
    logger = logging.getLogger('TAC_CASE_OBJ_BUILDER')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    if args.loggingLevel == "WARNING":
        ch.setLevel(logging.WARNING)
    elif args.loggingLevel == "DEBUG":
        ch.setLevel(logging.DEBUG)
    elif args.loggingLevel == "INFO":
        ch.setLevel(logging.INFO)
    elif args.loggingLevel == "ERROR":
        ch.setLevel(logging.ERROR)
    else:
        ch.setLevel(logging.CRITICAL)
    fh = logging.FileHandler('TAC_CASE_OBJ_BUILDER.log')
    fh.setLevel(logging.DEBUG)
    eh = logging.handlers.SMTPHandler('exit.vendor.com', 'WARNING_DO_NOT_REPLY@vendor.com',
                                      ['user1@vendor.com'], 'Message from TAC_CASE_OBJ_BUILDER application')
    eh.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    eh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.addHandler(eh)
    
    #tac = get_TACCase_objects(args.loggingLevel, _return_filter='all')