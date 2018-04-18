#!/usr/bin/env python

import argparse
import datetime
import pytz
from pytz import timezone 
import logging
import logging.handlers
import os
import pickle

import customer_automation_functions
import customer_account_variables
import customer_tfs_data_normalization

'''
###Moved these to the customer_account_variables module.###
_DDTS_TAC_CASE_PICKLE_JAR = '/Users/test/PythonQueues/tac_cases_DDTS/DDTS_TACCases.pkl'
_LASTXMIN_TAC_CASE_PICKLE_JAR = '/Users/test/PythonQueues/tac_cases_lastXmin/lastXmin_TACCases.pkl'
'''

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--loggingLevel",
                    choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                    default='WARNING', help="Enable console logging level.")
args = parser.parse_args()

logger = logging.getLogger('TAC_CASE_PICKLER')
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
#fh = logging.FileHandler(customer_account_variables.TAC_PICKLER_LOGFILE)
fh = logging.handlers.RotatingFileHandler(customer_account_variables.TAC_PICKLER_LOGFILE, maxBytes=50000000, backupCount=5)
fh.setLevel(logging.DEBUG)
eh = logging.handlers.SMTPHandler('outbound.vendor.com', 'WARNING_DO_NOT_REPLY@vendor.com',
                                  ['user1@vendor.com'], 'Message from customer_taccase_pickler application')
eh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
eh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)


utc = pytz.utc
pacific = timezone('US/Pacific')

_start_script_timestamp = datetime.datetime.now()
_start_script_timestamp_pst = pacific.localize(_start_script_timestamp)
_start_script_timestamp_utc = _start_script_timestamp_pst.astimezone(utc)
_10MinutesAgo = _start_script_timestamp_pst - datetime.timedelta(minutes=10)
_10MinutesAgo_utc = _start_script_timestamp_utc - datetime.timedelta(minutes=10)


TACCasesDict = {}
#Script runs every 10 minutes, via apple launchd, to collect TAC Case objects for open cases.
logger.info('Starting TAC_CASE_PICKLER script...')
logger.info('Calling customer_automation_functions.get_TACCase_objects_selenium()...')
logger.debug('logginLevel=%s, _status=default, _return_filter=None' % args.loggingLevel)
TACCasesDict = customer_automation_functions.get_TACCase_objects_selenium(args.loggingLevel, _return_filter=None)
#TACCasesDict = customer_automation_functions.get_TACCase_objects_selenium_threading(args.loggingLevel, _return_filter=None)
if len(TACCasesDict) >= 1:
    logger.info('customer_automation_functions.get_TACCase_objects_selenium() returned %i cases for analysis.' % len(TACCasesDict))
    logger.debug(TACCasesDict)
else:
    logger.info('customer_automation_functions.get_TACCase_objects_selenium() returned 0 cases for analysis.' % len(TACCasesDict))

#At the 4:30 PM PST run of the script we want to also run a collection of closed TAC cases that have DDTSs assigned to them.
#We'll check if the time of _start_script_timestamp is between 16:25PST and 16:35PST.  If it is we'll do the closed case collection.
if datetime.time(14, 25) < datetime.datetime.now().time() < datetime.time(14, 35):
    logger.info('Time is between 16:25 PST and 16:35 PST.  Running collection of closed TAC cases '
                + 'that have DDTSs noted in the case.')
    logger.info('Calling customer_automation_functions.get_TACCase_objects_selenium()...')
    logger.debug('logginLevel=%s, _status=closed_only, _return_filter=DDTS' % args.loggingLevel)
    logger.debug('logginLevel=%s, _status=default, _return_filter=None' % args.loggingLevel)
    closedTACCasesDict = customer_automation_functions.get_TACCase_objects_selenium(args.loggingLevel, _status='only_closed', _return_filter='DDTS')
    #closedTACCasesDict = customer_automation_functions.get_TACCase_objects_selenium_threading(args.loggingLevel, _status='only_closed', _return_filter='DDTS')
    if closedTACCasesDict >= 1:
        logger.info('There are %i closed cases with DDTSs assigned.' % len(closedTACCasesDict))
        logger.debug(closedTACCasesDict)
        logger.info('Adding %i closed cases to TACCasesDict.'% len(closedTACCasesDict))
        logger.debug(closedTACCasesDict)
        for key in closedTACCasesDict:
            TACCasesDict[key] = closedTACCasesDict[key]
            logger.debug('Added %s from case %s to TACasesDict' % (closedTACCasesDict[key], key))
        logger.debug(TACCasesDict)
    else:
        logger.info('There are 0 closed cases with DDTSs assigned.')

#At this point we should have TAC cases to parse.  If not just kill the program.
if len(TACCasesDict) == 0:
    logger.info('There are 0 cases for analysis.  Terminating program.')
    os.sys.exit(1)
    
DDTS_TACCasesDict = {}
lastXmin_TACCasesDict = {} #we'll need lastXmin to hunt for first webex entries for S1S2 cases.

#if there are tac cases in the dictionary look for cases with DDTS or cases created withing last 10 min create new dict(s) to be pickled.
_start_TACCasesDict_analysis_timestamp = datetime.datetime.now()
if TACCasesDict >= 1:
    logger.info('Parsing TAC cases for interesting information.')
    for case in TACCasesDict:
        try:
            if TACCasesDict[case].DDTS:
                #need to check if DDTS has already been submitted to TFS.  No need to put DDTS in pickle jar if it has been before.
                logger.info('Checking to see if DDTS %s has already been submitted to the TFS system...' % TACCasesDict[case].DDTS)
                in_tfs_request_queue = customer_automation_functions.in_tfs_request_queue(TACCasesDict[case].DDTS)
                if not in_tfs_request_queue['inQueue']:
                    logger.info('DDTS %s has not been previously submitted to the TFS system.' % TACCasesDict[case].DDTS)
                    DDTS_TACCasesDict[case] = TACCasesDict[case]
                    logger.debug('Added DDTS %s to DDTS_TACCasesDict from TAC case %s' % (TACCasesDict[case].DDTS, case))
        except Exception as e:
            logger.info('Failed to parse TAC case %s for DDTS information.' % case)
            logger.debug(e)
        else:
            if TACCasesDict[case].DDTS and in_tfs_request_queue['inQueue']:
                logger.info('DDTS %s has been previously submitted to the TFS system.' % TACCasesDict[case].DDTS)
            else:
                logger.info('No DDTS for TAC case %s' % case)
        try:
            logger.debug('createdTime=%s' % TACCasesDict[case].created)
            #TACCasesDict[case].created = TACCasesDict[case].created.replace(tzinfo=timezone('UTC')) #removed 22-jan-2017
            logger.debug('TAC case %s created %s.  startTimeUTC=%s, 10MinAgoUTC=%s.' % (TACCasesDict[case].caseNumber, TACCasesDict[case].created.astimezone(utc), _start_script_timestamp_utc, _10MinutesAgo_utc))
            logger.debug('TAC case %s created %s.  startTimePacific=%s, 10MinAgoPacific=%s.' % (TACCasesDict[case].caseNumber, TACCasesDict[case].created, _start_script_timestamp_pst, _10MinutesAgo))
            #Checking TACCasesDict[case].created against both local PST and UTC times.  This is because it looks like TAC cases stamp
            #TAC cases with UTC sometimes and local times at other times.  Will have to research this more.  Added everything after the or
            #for this fix.
            if (_10MinutesAgo_utc <= TACCasesDict[case].created.astimezone(utc) <= _start_script_timestamp_utc) or (_10MinutesAgo <= TACCasesDict[case].created  <= _start_script_timestamp_pst):
                lastXmin_TACCasesDict[case] = TACCasesDict[case]
            else:
                logger.debug('timeCreated not in last 10 minutes.') 
        except Exception as e:
            logger.info('Failed to parse TAC case %s for creation time information.' % case)
            logger.debug(e)
        else:
            if _10MinutesAgo_utc <= TACCasesDict[case].created.astimezone(utc) <= _start_script_timestamp_utc or (_10MinutesAgo <= TACCasesDict[case].created  <= _start_script_timestamp_pst):
                logger.debug('Added Case %s to lastXmin_TACCasesDict.' % case)
else:
    logger.info('There were 0 cases to look for DDTS or lastXmin.')
customer_automation_functions.runtime(_start_TACCasesDict_analysis_timestamp, 'TACCasesDict analysis', 'TAC cases', len(TACCasesDict))
    
_start_writingToDisk_timestamp = datetime.datetime.now()
numOfFiles = 0  #used for divisor in figuring out timestamp.
#New scripts will be kicked off when these pickle jars are put in the respective folders.  This is to get
#the action to be interrupt driven.
if len(DDTS_TACCasesDict) >= 1:
    numOfFiles += 1
    _deletedDDTSFile = False
    try:
        logger.info('Checking for existing DDTS pickle jar and erasing if found.')
        if os.path.exists(customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR):
            os.remove(customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR)
            _deletedDDTSFile = True
    except Exception as e:
        logger.info('Failed to check for or remove %s'  % customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR)
        logger.debug(e)
    else:
        if _deletedDDTSFile:
            logger.debug('Deleted %s.' % customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR)
    
    try:
        logger.info('Attempting to pickle DDTS_TACCasesDict...')
        f = open(customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR, 'wb')
        os.chmod(customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR, 0777)
        pickle.dump(DDTS_TACCasesDict, f)
        f.close()
    except Exception as e:
        logger.info('Failed to pickle /Users/test/PythonQueues/tac_cases_DDTS/DDTS_TACCases.pkl')
        logger.debug(e)
    else:
        logger.info('%i case(s) added to DDTS_TACCases.pkl' % len(DDTS_TACCasesDict))
        logger.info('Pickled %s.' % customer_account_variables.DDTS_TAC_CASE_PICKLE_JAR)
else:
    logger.info('There were no TAC cases in DDTS_TACCasesDict to pickle.')

if len(lastXmin_TACCasesDict) >= 1:
    numOfFiles += 1
    _deletedLastXminFile = False
    try:
        logger.info('Checking for existing lastXmin pickle jar and erasing if found.')
        if os.path.exists(customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR):
            os.remove(customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR)
            _deletedLastXminFile = True
    except Exception as e:
        logger.info('Failed to check for or remove %s.' % customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR)
        logger.debug(e)
    else:
        if _deletedLastXminFile:
            logger.debug('Deleted %s' % customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR)    
    
    try:
        logger.info('Attempting to pickle lastXmin_TACCasesDict...')
        f = open(customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR, 'wb')
        os.chmod(customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR, 0777)
        pickle.dump(lastXmin_TACCasesDict, f)
        f.close()
    except Exception as e:
        logger.info('Failed to pickle %s.' % customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR)
        logger.debug(e)
    else:
        logger.info('%i case(s) added to DDTS_TACCases.pkl' % len(lastXmin_TACCasesDict))
        logger.info('Pickled %s.' % customer_account_variables.LASTXMIN_TAC_CASE_PICKLE_JAR)
else:
    logger.info('There were no TAC cases in lastXmin_TACCasesDict to pickle.')
customer_automation_functions.runtime(_start_writingToDisk_timestamp, 'file writes', 'files', numOfFiles)
customer_automation_functions.runtime(_start_script_timestamp, 'script', 'TAC cases', len(TACCasesDict))
logger.info('Program complete.  Exiting normally')