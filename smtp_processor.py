#!/usr/bin/env python

import imaplib
import logging
import logging.handlers
import argparse
import datetime
import os

import customer_automation_functions
import customer_account_variables

_EMAIL_SERVER = 'mail.vendor.com'
_GENERIC_MAIL_USERNAME = 'xxxxx'
_GENERIC_MAIL_PASSWORD = 'xxxxx'
_DDTS_QUERY_SCRIPT = '/Users/test/PythonScripts/ddts_query.py'
_TFS_ADD_SCRIPT = '/Users/test/PythonScripts/customer_tfs_add_request_BETA.py'

def open_SMTP_connection():
    c = imaplib.IMAP4_SSL(_EMAIL_SERVER)
    return c

def mail_login(c):
    c.login(_GENERIC_MAIL_USERNAME, _GENERIC_MAIL_PASSWORD)

parser = argparse.ArgumentParser()
parser.add_argument("-l", "--loggingLevel",
                    choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                    default='WARNING', help="Enable console logging level.")
args = parser.parse_args()

logger = logging.getLogger('GET_MAIL')
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
#fh = logging.FileHandler(customer_account_variables.SMTP_PROCESSOR_LOGFILE)
fh = logging.handlers.RotatingFileHandler(customer_account_variables.SMTP_PROCESSOR_LOGFILE, maxBytes=50000000, backupCount=5)
fh.setLevel(logging.DEBUG)
eh = logging.handlers.SMTPHandler('outbound.vendor.com', 'WARNING_DO_NOT_REPLY@vendor.com',
                                  ['user1@vendor.com'], 'Message from customer_get_mail application')
eh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
eh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)

_start_script_timestamp = datetime.datetime.now()


cugIDs = []
subjectStart = []
subjectEnd = []
senderStart = []
senderEnd = []
senders = []
subjects = []


c = open_SMTP_connection()
mail_login(c)
c.select('INBOX')
cugIDs = c.search(None, 'ALL')[1]
cugIDs = cugIDs[0].split()

try:
    for (i,ID) in enumerate(cugIDs):
        logger.info('Finding "From" header start...')
        senderStart.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1].find('From: '))
        logger.debug('senderStart=%s' % senderStart[i])
        logger.info('Finding From: email address start character...')
        senderStart[i] = senderStart[i] + c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1][senderStart[i]:].find('<')
        logger.debug('senderStart=%s' % senderStart[i])
        logger.info('Skipping past From: email address start character...')
        senderStart[i] += 1
        logger.debug('senderStart=%s' % senderStart[i])
        logger.info('Finding From: email address end character...')
        senderEnd.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1][senderStart[i]:].find('>'))
        logger.debug('senderEnd=%s' % senderEnd[i])
        logger.info('Adjusting senderEnd number to include senderStart.')
        senderEnd[i] += senderStart[i]
        logger.debug('senderEnd=%s' % senderEnd[i])
        logger.info('Finding From: email address...')
        senders.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1][senderStart[i]: senderEnd[i]])
        logger.debug('sender=%s' % senders[i])
        logger.info('Finding "Subject: " header start...')
        subjectStart.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1].find('Subject: '))
        logger.debug('subjectStart=%s' % subjectStart[i])
        logger.info('Skipping past Subject: header start to subject...')
        subjectStart[i] += 9
        logger.debug('subjectStart=%s' % subjectStart[i])
        logger.info('Finding end of Subject: line...')
        subjectEnd.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1][subjectStart[i]:].find('\r\n'))
        logger.info('Adjusting subjectEnd to include subjectStart...')
        subjectEnd[i] += subjectStart[i]
        logger.debug('subjectEnd=%s' % subjectEnd[i])
        logger.info('Finding subject line...')
        subjects.append(c.fetch(ID, '(BODY.PEEK[HEADER])')[1][0][1][subjectStart[i]: subjectEnd[i]])
        logger.debug('subject=%s' % subjects[i])
except Exception as e:
    logger.exception(e)
else:
    logger.info('Finished parsing emails.')

for (i,subject) in enumerate(subjects):
    logger.info('Processing %i subject commands...' % len(subjects))
    logger.debug('i=%i, subject=%s' % (i, subjects[i]))
    if 'DDTS_QUERY_REQUEST' in subject:    
        logger.info('Processing DDTS query...')
        startPoint = subject.find('=')
        logger.debug('DDTS startPoint=%i' % startPoint)
        DDTS = subject[startPoint +1:]
        logger.debug('DDTS(s) in email subject header: %s' % DDTS)
        logger.info('Calling DDTS_QUERY_SCRIPT...')
        CMD = _DDTS_QUERY_SCRIPT + ' -l DEBUG -e ' + senders[i] + ' -d ' + DDTS
        logger.info(CMD)
        #os.system(_DDTS_QUERY_SCRIPT + ' -l DEBUG -e ' + senders[i] + ' -d ' + DDTS)
        os.system(CMD)
    elif 'TFS_ADD_BUG_REQUEST' in subject:
        logger.info('Processing TFS add request...')
        if subject[8: 11] == 'BUG':
            logger.info('TFS Request is for a software bug.')
            requestType = 'BUG'
        elif subject[8: 11] == 'FEA':
            logger.info('TFS request is for a new software feature.')
            requestType = 'FEATURE'
        startPoint = subject.find('=')
        logger.debug('DDTS startPoint=%i' % startPoint)
        DDTS = subject[startPoint +1:]
        logger.debug('DDTS(s) in email subject header: %s' % DDTS)
        logger.info('Calling TFS_ADD_%s_SCRIPT...' % requestType)
        os.system(_TFS_ADD_SCRIPT + ' -l DEBUG -t ' + requestType + ' -e ' + senders[i] + ' -d ' + DDTS)
    else:
        logger.info('No known command in subject line.  Doing nothing with email.')
        logger.debug('subject=%s, sender=%s' % (subject, senders[i]))

for ID in cugIDs:
    c.store(ID, '+FLAGS', r'(\Deleted)')
c.expunge()
c.close()
c.logout()
print 'logged out'