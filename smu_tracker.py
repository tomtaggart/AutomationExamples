#!/usr/bin/env python

import urllib2
import re
import base64
import sys
import logging
import logging.handlers
import datetime
import pytz
import json
import smtplib
from email.mime.text import MIMEText
import time
import argparse
import requests

from urlparse import urlparse
from bs4 import BeautifulSoup
import smartsheet

import customer_account_variables
import customer_automation_functions
import glog

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test_type", choices=['unit', 'functional'], \
                    help="DDTS is a bug or a feature request.")
parser.add_argument("-n", "--no_rebuild", action="store_true", help="Does not \
                    delete all rows and rebuild Smartsheet sheet during \
                    testing.")
parser.add_argument("-l", "--loggingLevel",
                    choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                    default='WARNING', help="Enable console logging level.")
args = parser.parse_args()

logger = logging.getLogger('bugTracker_SMARTSHEET_AUTOUPDATE')
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
fh = logging.handlers.RotatingFileHandler(customer_account_variables.bugTracker_SMARTSHEET_AUTOUPDATE_LOGFILE, maxBytes=50000000, backupCount=5)
fh.setLevel(logging.DEBUG)
eh = logging.handlers.SMTPHandler('outbound.vendor.com', 'WARNING_DO_NOT_REPLY@vendor.com',
                                  ['user1@vendor.com'], 'Message from customer_SMU_TRACKER application')
eh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
eh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)

logger.info('Setting team email...')
if args.test_type:
    TEAM_EMAIL = 'user1@vendor.com'
else:
    TEAM_EMAIL = 'customer-cloudcarrier-wan@vendor.com'
logger.debug('=%s' % TEAM_EMAIL)
logger.info('Setting smartsheet sheet ID...')
if args.test_type == 'functional':
    #FunctionalTestbed Smartsheet
    #https://app.smartsheet.com/b/xxxxx
    SMARTSHEET_SMU_TRACKER_SHEET_ID = 'xxxxx'
elif args.test_type == 'unit':
    #UnitTestbed Smartsheet
    #https://app.smartsheet.com/b/xxxxx
    SMARTSHEET_SMU_TRACKER_SHEET_ID = 'xxxxx'
else:
   #Production Smartsheet
   #https://app.smartsheet.com/b/xxxxx
   SMARTSHEET_SMU_TRACKER_SHEET_ID = 'xxxxx'
logger.debug('SMARTSHEET_SMU_TRACKER_SHEET_ID=%s' % SMARTSHEET_SMU_TRACKER_SHEET_ID)

   
EMAIL_TAIL = '\n\n\nPlease see https://app.smartsheet.com/b/xxxxx for additional details.'

# Links removed for security reasons

SMU_URL_LIST = [
                bugTracker_525_SMU_URL, bugTracker_526_SMU_URL,
                bugTracker_600_SMU_URL, bugTracker_601_SMU_URL, bugTracker_602_SMU_URL,
                bugTracker_611_SMU_URL, bugTracker_612_SMU_URL, bugTracker_613_SMU_URL, bugTracker_614_SMU_URL,
                bugTracker_621_SMU_URL, bugTracker_6211_SMU_URL,
                bugTracker_622_SMU_URL, bugTracker_6225_SMU_URL,
]

bugTracker_SMU_RECORD_URL = 'http://bugTracker-web.vendor.com/bugTracker-home/fcgi-bin/SMU/SmuDetails.cgi?smu_id='

_start_script_timestamp = datetime.datetime.utcnow()

def chunks(L, n):
    """Take a list, L, and break it down into successive n-sized chunks."""
    logger = logging.getLogger('bugTracker_SMARTSHEET_AUTOUPDATE.chunks')
    logger.info('Slicing bugTracker chart into 25 <td> pieces...')
    return [L[i:i + n] for i in xrange(0, len(L), n)]

def getURL(_URL):
    logger = logging.getLogger('bugTracker_SMARTSHEET_AUTOUPDATE.getURL')
    logger.info('Attempting to open URL %s...' % _URL)
    req = urllib2.Request(_URL)
    try:
        response = urllib2.urlopen(req)
    #except IOError as e:
    except Exception as err:
        # here we *want* to fail
        e = err
        pass
    else:
        # If we don't fail then the page isn't protected
        logger.info("This page isn't protected by authentication.  Exiting application.")
        sys.exit(1)
    logger.info('Validating initial attempt failed due to authentication challenge...')
    if not hasattr(e, 'code') or e.code != 401:
        # we got an error - but not a 401 error
        logger.info("This page isn't protected by authentication.")
        logger.info('But we failed for another reason.')
        logger.debug(e)
        sys.exit(1)
    logger.info('Retrieving authentication scheme and realm...')
    logger.info('Pulling www-authenticate line from header...')
    authline = e.headers['www-authenticate']
    # this gets the www-authenticate line from the headers
    # which has the authentication scheme and realm in it
    logger.debug('authline=%s' % authline)
    logger.info('Creating RE to parse www-authenticate line for scheme and realm...') #<========stopped logging here.
    authobj = re.compile(
        r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"]([^'"]+)['"]''',
        re.IGNORECASE)
    # this regular expression is used to extract scheme and realm
    matchobj = authobj.match(authline)
    
    if not matchobj:
        # if the authline isn't matched by the regular expression
        # then something is wrong
        print 'The authentication header is badly formed.'
        print authline
        sys.exit(1)
    
    scheme = matchobj.group(1)
    realm = matchobj.group(2)
    # here we've extracted the scheme
    # and the realm from the header
    if scheme.lower() != 'basic':
        print 'This example only works with BASIC authentication.'
        sys.exit(1)
    
    base64string = base64.encodestring(
                    '%s:%s' % (glog.foo, glog.bar()))[:-1]
    authheader =  "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    try:
        response = urllib2.urlopen(req)
    except IOError:#, e:
        # here we shouldn't fail if the username/password is right
        print "It looks like the username or password is wrong."
        sys.exit(1)
    html = response.read()
    return html

def getSMURecord(SMU_ID):
    def makeEntry(value):
        SMURecordDetail[str(line.next_element).strip(': ')] = {
                u'value' : value,
                u'url' : False,
                u'changedCell': False,
        }
            
    SMURecordDetail = {}
    SMURecordURL = getURL(bugTracker_SMU_RECORD_URL + SMU_ID)
    SMURecordSoup = BeautifulSoup(SMURecordURL, 'html.parser')
    SMURecordTds = SMURecordSoup.findAll('td')
    for line in SMURecordTds:
        value = ''
        if line.get_text(value) == 'DDTS Component:':
            value = str(line.next_element.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() == ' SMU Type: ':
            value = str(line.next_element.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() == ' Reload SMU: ':
            value = str(line.next_element.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() == ' SMU Installation Impact: ':
            value = str(line.next_element.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() == 'Image MD5:':
            value = str(line.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() == 'Restart Type:':
            value = str(line.next_element.next_element.next_element).strip(': ')
            makeEntry(value)
        elif line.get_text() ==  ' Constituent DDTS: ':
            constituent_DDTS_pattern = re.compile(r'CSC[\w]{2}[\d]{5}')
            constituent_DDTS_match = str(constituent_DDTS_pattern.findall(str(line.next_element.next_element.next_element))).strip('[]')
            value = re.sub("'", '', constituent_DDTS_match)
            makeEntry(value)
        elif line.get_text() == 'ISSU Flag:': 
            input_pattern = re.compile(r'<input checked=""[^>]*>')
            match = input_pattern.search(str(line.next_element.next_element)).group()
            yesNo_pattern = re.compile(r'value="(.*)"')
            value = yesNo_pattern.search(match)
            SMURecordDetail[str(line.next_element).strip(': ')] =  {u'value' : value.groups()[0],
                                                                    u'url' : False,
                                                                    u'changedCell': False,
                                                                    }
    return SMURecordDetail 

def sendmail(msg):
    try:
        emailMessage = MIMEText(msg)
    except Exception as e:
            logger.warning('Could not create email message: %s.' % msg)
            logger.debug(e)
    else: 
        emailMessage['Subject'] = "SMU List Smartsheet Changes"
        emailMessage['To'] = TEAM_EMAIL
        emailMessage['Sender'] = 'xxxxxn@vendor.com'
        emailMessage['Reply-To'] = 'xxxxx'
        try:
            logger.info('Connecting to SMTP server...')
            SMTP_CONNECTION = smtplib.SMTP('xxxxx.vendor.com:25')
        except Exception as e:
            logger.warning('Connection to vendor SMTP server for SMU Tracker application failed.')
            logger.debug(e)
        else:
            try:
                logger.info('Sending cell change email to vendor SMTP server for SMU Tracker application.')
                SMTP_CONNECTION.sendmail('user1@vendor.com', TEAM_EMAIL, emailMessage.as_string())
            except Exception as e:
                logger.info('Cell change email could not be sent to xxxxx.vendor.com:25 for SMU Tracker application.')
                logger.debug(e)
                logger.warning('Cell change email could not be sent to xxxxx.vendor.com:25 for SMU Tracker application.')
            else:
                logger.info('Successfully sent cell change email to vendor SMTP server for SMU Tracker application.')
            if SMTP_CONNECTION:
                SMTP_CONNECTION.quit() 


def createSmartsheetDict(SSID=SMARTSHEET_SMU_TRACKER_SHEET_ID):
    ###Connect to Smartsheet website requesting archived SMU information
    ###
    #Create Smartsheet Object for User Token
    #if not smartsheet:
    import smartsheet
    smartsheet = smartsheet.Smartsheet(glog.SMU_TRACKER_SMARTSHEET_TOKEN)
    #Create Smartsheet Object for SMU_Tracker Sheet
    SMUTrackerSmartsheet = smartsheet.Sheets.get_sheet(SSID, page_size=1000)
    
    SMARTSHEET_SMU_DICT = {}
    SMARTSHEET_ColumnName_ID_Dict = {}
    SMARTSHEET_ColumnName_ID_Dict2 = {}
    for obj in SMUTrackerSmartsheet.columns:
        SMARTSHEET_ColumnName_ID_Dict[obj.id] = obj.title
        SMARTSHEET_ColumnName_ID_Dict2[obj.title] = obj.id
        if obj.title == u'SMU ID':
            SMARTSHEET_PRIMARY_COLUMN_ID = obj.id
    for row in SMUTrackerSmartsheet.rows:
        for cell in row.cells:
            if cell.column_id == SMARTSHEET_PRIMARY_COLUMN_ID:  
                SMARTSHEET_SMU_DICT_KEY = cell.value
        SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY] = {u'rowID' : row._Row__id}
        for cell in row.cells:
            #When cells from bugTracker and SMARTSHEET are u'\xa0' they don't compare correctly.  Cleaning field to be Python None.
            if cell.value == u'\xa0':
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]] = {u'value' : None}
            else:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]] = {u'value' : cell.value}
            SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'columnID'] = cell.column_id
            if cell.hyperlink:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'url'] = cell.hyperlink
            else:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'url'] = False
    return SMARTSHEET_SMU_DICT

def CREATE_bugTracker_SMU_DICT():
    ###
    ###Connect to websites and return html page
    ###    
    logger = logging.getLogger('bugTracker_SMARTSHEET_AUTOUPDATE.CREATE_bugTracker_SMU_DICT')
    bugTracker_SMU_DICT = {}
    
    for website in SMU_URL_LIST:
        html = getURL(website)   
        #Create BeautifulSoup object, ingest in HTML file, and parse for
        #bugTracker <th> & <td> fields.                                               #<========started logging again here.
        logger.info('Creating beautifulsoup instance...')
        soup = BeautifulSoup(html, 'html.parser')
        logger.info('Parsing for bugTracker SMU column headers...')
        tableHeaders = soup.find_all('th')
        logger.info('bugTracker SMU column headers parsed.')
        logger.debug(tableHeaders)
        #tableHeaders is a bs4 object so I need to take out text from
        #<th> tags and put into list which can be zipped to actual cell
        #data later.
        logger.info('Pulling column header text from bs4 objects...')
        tableHeadersList = []
        for line in tableHeaders:
            tableHeadersList.append(line.get_text())
        logger.debug(tableHeadersList)
        logger.info('Parsing for bugTracker SMU column data...')  
        AllTableData = soup.find_all('td')
        #Removing first five lines as they are generic to HTML body and
        #not the bugTracker SMU data tabel itself.    
        AllTableData = AllTableData[5:]
        #AllTableData is a bs4 object so I need to take out text and URL
        #from <td> tags and put into list which can be zipped to header
        #cell data later.
        logger.info('Pulling cell data text and URLs from bs4 objects...')
        AllTableDataList = []
        for line in AllTableData:
            data = {}
            data[u'text'] = line.get_text()     
            alinks = line.find_all('a')
            if len(alinks) == 1:
                data[u'url'] = alinks[0]['href']
                if 'bugTracker-home' in data[u'url']:
                    data[u'url'] = 'http://bugTracker-web.vendor.com' + data[u'url'] #need to troubleshoot bs4, not getting first part of URL
            AllTableDataList.append(data)
        #Some cells have multiple lines of SMU ID data. In an effort to turn this
        #information into a list I break the string into separate lines when a new
        #SMU ID is encountered.  Doing this has some anomolies so I have to tweak
        #the resultant data to get the 'AA' back onto SMU IDs.       
        for i,line in enumerate(AllTableDataList):
            if 'AA' in line and 'CSC' in line[u'text']:
                AllTableDataList[i][u'text'] = line[u'text'].split('AA')
                for x,entry in enumerate(AllTableDataList[i][u'text']):
                    AllTableDataList[i][u'text'][x] = 'AA' + AllTableDataList[i][u'text'][x]
                for x,entry in enumerate(AllTableDataList[i][u'text']):
                    if AllTableDataList[i][u'text'][x] == u'AA':
                       AllTableDataList[i][u'text'].pop(x)
                '\n'.join(AllTableDataList[i][u'text'])
                
        logger.debug(AllTableDataList)
        #We now have one big list with all the cell data from the bugTracker SMU table.
        #There are 25 columns in the table so we need to convert the big list,
        #which has a total 25 X the number of SMUs, into a list containing a
        #series of lists each 25 cells long.
        logger.info('Breaking AllTableDataList into 25 column sections...')
        SeperatedTableData = []
        SeperatedTableData = chunks(AllTableDataList, 25)
        logger.debug(SeperatedTableData)
        logger.info('Zipping table headers to table cell data...')
        for i,list_ in enumerate(SeperatedTableData):
           SeperatedTableData[i] = zip(tableHeadersList, SeperatedTableData[i]) 
        for i,list_ in enumerate(SeperatedTableData):
            SeperatedTableData[i] = dict(list_)
        logger.info('SeperatedTableData dictionary created.')
        logger.debug(SeperatedTableData)
        
        logger.info('Creating bugTracker_SMU_DICTIONARY...')
        for dictionary in SeperatedTableData:
            logger.info('Creating row entry for %s...' % dictionary[u'SMU ID'][u'text'])
            bugTracker_SMU_DICT[dictionary[u'SMU ID'][u'text']] = {u'newRow' : False,
                                                             u'changedRow': False,
                                                             u'rowID' : 0
                                                            }
            logger.info('Row entry for %s created.' % dictionary[u'SMU ID'][u'text'])
            logger.debug(bugTracker_SMU_DICT[dictionary[u'SMU ID'][u'text']])
            #Create SMU record
            #SMU_Record_Dictionary = getSMURecord(dictionary[u'SMU ID'][u'text'])
            for key in dictionary:
                logger.info('Creating cell entry %s for %s...' % (key, dictionary[u'SMU ID'][u'text']))
                if dictionary[key][u'text'] == u'\xa0':
                    bugTracker_SMU_DICT[dictionary[u'SMU ID']['text']][key] = {u'value' : None,
                                                                         u'changedCell' : False,
                                                                         u'columnID' : 0,
                                                                        }
                else:
                    bugTracker_SMU_DICT[dictionary[u'SMU ID']['text']][key] = {u'value' : dictionary[key][u'text'],
                                                                         u'changedCell' : False,
                                                                         u'columnID' : 0,
                                                                        }
                
                
                logger.info('Adding URL to cell entry %s for %s if present...' % (key, dictionary[u'SMU ID'][u'text']))
                
                #Add information from SMU record webpage
                #bugTracker_SMU_DICT[dictionary[u'SMU ID']['text']][key].update(SMU_Record_Dictionary)
                try:
                    bugTracker_SMU_DICT[dictionary[u'SMU ID'][u'text']][key][u'url'] = dictionary[key][u'url']
                    logger.info('Added URL to cell entry %s for %s if present...' % (key, dictionary[u'SMU ID'][u'text']))            
                except:
                    bugTracker_SMU_DICT[dictionary[u'SMU ID'][u'text']][key][u'url'] = False
                    logger.info('Set URL to cell entry %s for %s to False...' % (key, dictionary[u'SMU ID'][u'text'])) 
            logger.info('Row for %s created.' % dictionary[u'SMU ID'][u'text'])
            logger.debug(bugTracker_SMU_DICT[dictionary[u'SMU ID'][u'text']])
        logger.info('bugTracker_SMU_DICTIONARY created.')
        logger.debug(bugTracker_SMU_DICT)
    return bugTracker_SMU_DICT







if __name__ == '__main__':
    ###
    ###Connect to Smartsheet website requesting archived SMU information
    ###
    #Create Smartsheet Object for User Token
    #if not smartsheet:
    smartsheet = smartsheet.Smartsheet(glog.SMU_TRACKER_SMARTSHEET_TOKEN)
    #Create Smartsheet Object for SMU_Tracker Sheet
    SMUTrackerSmartsheet = smartsheet.Sheets.get_sheet(SMARTSHEET_SMU_TRACKER_SHEET_ID, page_size=1000)
    
    SMARTSHEET_SMU_DICT = {}
    SMARTSHEET_ColumnName_ID_Dict = {}
    SMARTSHEET_ColumnName_ID_Dict2 = {}
    for obj in SMUTrackerSmartsheet.columns:
        SMARTSHEET_ColumnName_ID_Dict[obj.id] = obj.title
        SMARTSHEET_ColumnName_ID_Dict2[obj.title] = obj.id
        if obj.title == u'SMU ID':
            SMARTSHEET_PRIMARY_COLUMN_ID = obj.id
    for row in SMUTrackerSmartsheet.rows:
        for cell in row.cells:
            if cell.column_id == SMARTSHEET_PRIMARY_COLUMN_ID:  
                SMARTSHEET_SMU_DICT_KEY = cell.value
        SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY] = {u'rowID' : row._Row__id}
        for cell in row.cells:
            #When cells from bugTracker and SMARTSHEET are u'\xa0' they don't compare correctly.  Cleaning field to be Python None.
            if cell.value == u'\xa0':
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]] = {u'value' : None}
            else:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]] = {u'value' : cell.value}
            SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'columnID'] = cell.column_id
            if cell.hyperlink:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'url'] = cell.hyperlink
            else:
                SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY][SMARTSHEET_ColumnName_ID_Dict[cell.column_id]][u'url'] = False
    SMUS_IN_SMARTSHEET_LIST = SMARTSHEET_SMU_DICT.keys()
    
    bugTracker_SMU_DICT = CREATE_bugTracker_SMU_DICT()
    
        
    #indent below block if turning back on above commented out bugTracker section    
    #Set rowID in the bugTracker_SMU_DICT
    SMU_ID_TO_ROW_ID_DICT = {}
    for row in SMUTrackerSmartsheet.rows:
        D = row.cells[0].to_json()
        D = json.loads(D)
        SMU_ID_TO_ROW_ID_DICT[D["value"]] = row.id
    for SMU_ID in bugTracker_SMU_DICT:
        if SMU_ID_TO_ROW_ID_DICT.has_key(SMU_ID):
            bugTracker_SMU_DICT[SMU_ID][u'rowID'] = SMU_ID_TO_ROW_ID_DICT[SMU_ID]
           
    
    #Add DDTS integrated in information
    for SMU_ID in bugTracker_SMU_DICT:
        if SMU_ID not in SMUS_IN_SMARTSHEET_LIST:
            #Add integrated SW field from QDDTS via BDB script
            DDTSDetails = customer_automation_functions.bdb_borgv3_bug_api(
                    bugTracker_SMU_DICT[SMU_ID]['DDTS']['value'],'DEBUG'
            )
            integratedIn = str(DDTSDetails['integrated'])
            bugTracker_SMU_DICT[SMU_ID]['Integrated In SW Version'] = {
                    u'value' : integratedIn,
                    u'changedCell' : False,
                    u'columnID' : 0,
                    u'url' : False,
            }
    
    logger.debug('Checking for changes in cells...')
    #Check for changes and set changed or new flag in bugTracker_SMU_DICT
    changedRowsCounter = 0
    newRows = 0
    for SMU_ID in bugTracker_SMU_DICT:
        if SMU_ID not in SMUS_IN_SMARTSHEET_LIST:
            bugTracker_SMU_DICT[SMU_ID][u'newRow'] = True
            newRows += 1
            #Add SMU Record information
            SMU_Record_Dictionary = getSMURecord(SMU_ID)
            bugTracker_SMU_DICT[SMU_ID].update(SMU_Record_Dictionary)
            
            #Get Release Notes   <-------------------------------------------------------------------Working Here
            
            interesting_ddtss = []
            release_notes = ''
            interesting_ddtss.append(bugTracker_SMU_DICT[SMU_ID]['DDTS']['value'])
            ddts_pattern = re.compile(r'CSC[a-z]{2}[\d]{5}')
            ddts_match = ddts_pattern.findall(bugTracker_SMU_DICT[SMU_ID]['Constituent DDTS']['value'])
            if ddts_match:
                interesting_ddtss.extend(ddts_match)
            if len(interesting_ddtss) > 0:
                for ddts in interesting_ddtss:
                    release_notes = (release_notes
                                     + ddts
                                     + ':\n'
                                     + customer_automation_functions.get_cdets_ddts_release_note(ddts, 'DEBUG')
                                     + '\n\n'
                    )
            SMU_Release_Notes_Dictionary = {}
            SMU_Release_Notes_Dictionary['Release Notes'] =  {
                u'value' : release_notes,
                u'url' : False,
                u'changedCell': False,
            }
            bugTracker_SMU_DICT[SMU_ID].update(SMU_Release_Notes_Dictionary)
            
    
    changedCellDict = {}
    for SMU_ID in bugTracker_SMU_DICT:
        if not bugTracker_SMU_DICT[SMU_ID][u'newRow']:
            for cellAttribute in bugTracker_SMU_DICT[SMU_ID]:  #-----This is an entire row
                if cellAttribute not in (u'newRow', u'changedRow', u'rowID', u'release_note',
                                         u'SMU Name', u'DE', u'DE Mgr', u'DT Mgr', u'Requester'):
                    '''
                    print SMARTSHEET_SMU_DICT[SMU_ID]
                    print SMU_ID
                    print 'cellAttribute: ', cellAttribute
                    print 'bugTracker: ', bugTracker_SMU_DICT[SMU_ID][cellAttribute][u'value']
                    print 'SS: ', SMARTSHEET_SMU_DICT[SMU_ID][cellAttribute][u'value']
                    '''
                    
                    if bugTracker_SMU_DICT[SMU_ID][cellAttribute][u'value'] != SMARTSHEET_SMU_DICT[SMU_ID][cellAttribute][u'value']:
                        bugTracker_SMU_DICT[SMU_ID][cellAttribute]['changedCell'] = True
                        #print 'SMU_ID_TO_ROW_ID_DICT: ', SMU_ID_TO_ROW_ID_DICT
                        #raw_input('stop')
                        if not changedCellDict.has_key(SMU_ID_TO_ROW_ID_DICT[SMU_ID]):
                            changedCellDict[SMU_ID_TO_ROW_ID_DICT[SMU_ID]] = {}
                        changedCellDict[SMU_ID_TO_ROW_ID_DICT[SMU_ID]] = {u'SMU_ID' : SMU_ID}
                        changedCellDict[SMU_ID_TO_ROW_ID_DICT[SMU_ID]][SMARTSHEET_ColumnName_ID_Dict2[cellAttribute]] = {
                                u'SMU_ID' : SMU_ID,
                                u'columnName' : cellAttribute,
                                u'rowID' : bugTracker_SMU_DICT[SMU_ID]['rowID'],
                                u'columnID' : SMARTSHEET_ColumnName_ID_Dict2[cellAttribute],
                                u'new_bugTracker_cell_Value' : bugTracker_SMU_DICT[SMU_ID][cellAttribute][u'value'],
                                u'old_SMARTSHEET_cell_value' : SMARTSHEET_SMU_DICT[SMU_ID][cellAttribute][u'value'],
                                #u'DDTS_Headline' : bugTracker_SMU_DICT[SMU_ID][u'DDTS Headline'][u'value'],
                        }
                        if not bugTracker_SMU_DICT[SMU_ID][u'changedRow']:
                            bugTracker_SMU_DICT[SMU_ID][u'changedRow'] = True
                            changedRowsCounter += 1
    
    #Add Modify existing rows changed cells to Smartsheet
    rowPostSuccesses = []
    changedCellEmail = False
    if changedRowsCounter >0:
        #using requests to push row changes.  Tried the python SDK and it was too buggy to be relied upon.
        changedRowsList = []
        for i,changedCellRow in enumerate(changedCellDict):
            changedRowsList.append({"id" : changedCellRow, "cells" : []})
            for changedCell in changedCellDict[changedCellRow]:    
                if changedCell not in [u'SMU_ID']:
                    changedRowsList[i]['cells'].append(
                            {
                             "columnId" : changedCellDict[changedCellRow][changedCell][u'columnID'],
                             "value" : changedCellDict[changedCellRow][changedCell][u'new_bugTracker_cell_Value']
                             }
                    )   
        url = u'https://api.smartsheet.com/2.0/sheets/%s/rows' % SMARTSHEET_SMU_TRACKER_SHEET_ID
        token = u'Bearer ' + glog.SMU_TRACKER_SMARTSHEET_TOKEN
        headers = {u'Authorization' : token, u'Content-Type' : u'application/json'}
        r = requests.put(url, headers=headers, json=changedRowsList)
        check = json.loads(r.text)
        if check['message'] == 'SUCCESS':
            changedCellEmail = True

    for row in SMUTrackerSmartsheet.rows:
        for cell in row.cells:
            if cell.column_id == SMARTSHEET_PRIMARY_COLUMN_ID:  
                SMARTSHEET_SMU_DICT_KEY = cell.value
        SMARTSHEET_SMU_DICT[SMARTSHEET_SMU_DICT_KEY] = {u'rowID' : row._Row__id}

    logger.debug('Adding rows to smartsheet...')
    #Add new rows to Smartsheet
    newRowsEmail = False
    if newRows > 0:
        newRowObjects = [smartsheet.models.Row() for x in range(newRows)]
        i = 0
        #for i, SMU_ID in enumerate(bugTracker_SMU_DICT):
        for SMU_ID in bugTracker_SMU_DICT:
            if bugTracker_SMU_DICT[SMU_ID][u'newRow']:
                newRowObjects[i].to_bottom = True
                newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[u'Needs Review'],
                                               'value' : 'Internal vendor',
                                               'strict': False
                                              })
                if u'NCS' in bugTracker_SMU_DICT[SMU_ID][u'Platform'][u'value'] or u'ASR' in bugTracker_SMU_DICT[SMU_ID][u'Platform'][u'value']:
                    newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[u'OS Type'],
                                                   'value' : 'IOS XR',
                                                   'strict': False
                                                  })
                if u'sysadmin' in bugTracker_SMU_DICT[SMU_ID][u'Platform'][u'value']:    
                    newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[u'Sysadmin or XR SMU'],
                                                   'value' : 'sysadmin',
                                                   'strict': False
                                                  })
                else:
                    newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[u'Sysadmin or XR SMU'],
                                                   'value' : 'xr',
                                                   'strict': False
                                                  })
            
                for cell in bugTracker_SMU_DICT[SMU_ID]:
                    if cell not in (u'newRow', u'changedRow', u'rowID', u'release_note'):
                        if bugTracker_SMU_DICT[SMU_ID][cell][u'url']:
                            newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[cell],
                                                           'value' : bugTracker_SMU_DICT[SMU_ID][cell][u'value'],
                                                           'hyperlink' : {'url': bugTracker_SMU_DICT[SMU_ID][cell][u'url']},
                                                           #'hyperlink' : bugTracker_SMU_DICT[SMU_ID][cell][u'url'],
                                                           'strict': False,
                                                          })
                        else:
                            newRowObjects[i].cells.append({'column_id' : SMARTSHEET_ColumnName_ID_Dict2[cell],
                                                           'value' : bugTracker_SMU_DICT[SMU_ID][cell][u'value'],
                                                           'strict': False,
                                                          })
                i += 1
        newRowsEmail = True
        logger.debug('writing to smartsheet...')
        
        newRowAction = smartsheet.Sheets.add_rows(SMARTSHEET_SMU_TRACKER_SHEET_ID, newRowObjects)
        #print(newRowAction)
        
        
    message = ('Team,\n\nThe following changes have been made to the Golden SMU List on Smartsheet via automation.\n'
              + 'We are tracking the following releases via this tool:\n    '
    )
    version_pattern = re.compile(r'[\d]{1,4}')
    message += ", ".join(version_pattern.findall(", ".join([X for X in dir() if X[-3:] == "URL"]))) + '.\n\n'
    if changedCellEmail:
    #if action.message == u'SUCCESS':
        #Email cell changes to team alias
        message = message + 'The following cells have changed:\n'
        for changedCellRow in changedCellDict:
            message = message + '  For SMU %s in %s, %s:\n' % (
                changedCellDict[changedCellRow][u'SMU_ID'],
                bugTracker_SMU_DICT[changedCellDict[changedCellRow][u'SMU_ID']][u'Release'][u'value'],
                bugTracker_SMU_DICT[changedCellDict[changedCellRow][u'SMU_ID']][u'DDTS Headline'][u'value'],
            )
            for changedCell in changedCellDict[changedCellRow]:
                if changedCell not in [u'SMU_ID']:
                    message = message + '    Cell "%s" has changed from "%s" to "%s"\n' % (
                            changedCellDict[changedCellRow][changedCell][u'columnName'],
                            changedCellDict[changedCellRow][changedCell][u'old_SMARTSHEET_cell_value'],
                            changedCellDict[changedCellRow][changedCell][u'new_bugTracker_cell_Value'],
                    )
            message = message + '\n'
    
    if newRowsEmail: #if newRowAction.message == u'SUCCESS':
        #Email cell changes to team alias
        message = message + 'The following SMU(s) have been added:\n'
        for SMU_ID in bugTracker_SMU_DICT:
            if bugTracker_SMU_DICT[SMU_ID][u'newRow']:
                message = message + '  %s in %s: %s\n' % (
                        SMU_ID,
                        bugTracker_SMU_DICT[changedCellDict[changedCellRow][u'SMU_ID']][u'Release'][u'value'],
                        bugTracker_SMU_DICT[SMU_ID][u'DDTS Headline'][u'value']
                )
        
    if changedCellEmail or newRowsEmail:    
        message = message + EMAIL_TAIL
        sendmail(message)
    #need to indent above if turning back on create bugTracker section
    
    _stop_script_timestamp = datetime.datetime.utcnow()
    logger.info('TOTAL_SCRIPT_RUNTIME=%s' % (_stop_script_timestamp - _start_script_timestamp))
    
    