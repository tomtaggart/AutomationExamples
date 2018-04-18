#!/usr/bin/env python

import logging
from logging import handlers
import requests
import json
import re

from bs4 import BeautifulSoup

import glog
import customer_account_variables

logger = logging.getLogger('customer_tfs_data_normalization')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
#fh = logging.FileHandler(customer_account_variables.TFS_LOGFILE)
fh = logging.handlers.RotatingFileHandler(customer_account_variables.TFS_LOGFILE, maxBytes=50000000, backupCount=5)
fh.setLevel(logging.DEBUG)
eh = logging.handlers.SMTPHandler('xxxxx', 'xxxxxx',
                                  ['xxxxx'], 'Message from DDTS_QUERY application')
eh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s [%(name)s]-%(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
eh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)


def node_name(caseNumber):
    logger = logging.getLogger('customer_tfs_data_normalization.node_name')    
    logger.info('Collecting casekwery webpage...')
    r = requests.get('http://www-tac.vendor.com/Teams/ks/c3/casekwery.php?Case=%s' % caseNumber, auth=(glog.foo, glog.bar()))
    logger.info('Recieved casekwery webpage.')
    
    ''' removed due to moving toward regular expression matching as hostname entry in tac case is so elusive
    r10Start = r.text.find('r10')
    logger.debug('r10Start=%i' % r10Start)
    if r10Start != -1:
        r10End = r.text[r10Start:].find(" ")
        r10End += r10Start
        hostname = r.text[r10Start: r10End]
    '''
    
    logger.info('Creating regular expressions for hostname patterns...')
    #GeneralHostnamePattern = re.compile('([a-z0-9]{5})\.([a-z0-9]{3,5})\.?([a-z0-9]{3,5})?')
    r1HostnamePattern = re.compile('(r10[12])\.([a-z0-9]{3,5})\.?([a-z0-9]{3,5})?')
    r2HostnamePattern = re.compile('(icr0[1234])\.([a-z0-9]{3,5})\.?([a-z0-9]{3,5})?')
    #removing DC hostname matching when searching notes HTML page as it returns html code
    #probably best way to readd this in future is to create a list of 2-6 character English words
    #then iterate through .groups() list in RE.match object to be sure the names aren't English words
    #this may still not be good enough but it's an idea
    #DCHostnamePattern1 = re.compile('".*([a-z0-9]{3,6})-([a-z0-9]{3,6})-([a-z0-9]{1,6})-?([a-z0-9]{1,6})?-?([a-z0-9]{1,6})?.*"')
    #DCHostnamePattern2 = re.compile('([a-z0-9]{3,6})-([a-z0-9]{3,6})-([a-z0-9]{1,6})-?([a-z0-9]{1,6})?-?([a-z0-9]{1,6})?')
    logger.info('Searching casekwery page for r1 hostname...')
    hostname = r1HostnamePattern.search(r.text.lower())
    if not hostname:
        hostname = r2HostnamePattern.search(r.text.lower())
    '''
    if not hostname:
        hostname = DCHostnamePattern1.search(r.text.lower())
        if hostname:
            hostname = DCHostnamePattern2.search(hostname.group())
    '''
    if not hostname:
        hostname = 'TBD'   
    else:
        hostname = hostname.group()
    logger.debug('hostname=%s' % hostname)
    return hostname

def validate_node_name(hostname):
    r1HostnamePattern = re.compile('(r10[12])\.([a-z0-9]{3,5})\.?([a-z0-9]{3,5})?')
    r2HostnamePattern = re.compile('(r20[1234])\.([a-z0-9]{3,5})\.?([a-z0-9]{3,5})?')
    DCHostnamePattern = re.compile('([a-z0-9]{3,6})-([a-z0-9]{3,6})-([a-z0-9]{1,6})-?([a-z0-9]{1,6})?-?([a-z0-9]{1,6})?')
    scrubbedHostname = r1HostnamePattern.search(hostname)
    if not scrubbedHostname:
        scrubbedHostname = r2HostnamePattern.search(hostname)
    if not scrubbedHostname:
        scrubbedHostname = DCHostnamePattern.search(hostname)
    if scrubbedHostname:
        return scrubbedHostname.group()
    else:
        return False
        


def review_required(reason):
    logger = logging.getLogger('customer_tfs_data_normalization.review_required')  
    if reason == 'initialAdd':
        review = 'Yes'
    else:
        review = False
    logger.debug('review_required set to %s' % review)
    return review
    
def review_required_comments(reason):
    logger = logging.getLogger('customer_tfs_data_normalization.review_required_comments')
    if reason == 'initialAdd':
        comments = 'New Defect'
    else:
        comments = False
    logger.debug('review_required_comments set to %s' % comments)
    return comments

def feature_status(reason):
    logger = logging.getLogger('customer_tfs_data_normalization.feature_status')
    if reason == 'initialAdd':
        status = 'Requested (or RCA)'
    else:
        pass
    logger.debug('feature_status set to %s' % status)
    return status

def product_stats(product, hostname):
    logger = logging.getLogger('customer_tfs_data_normalization.product_stats')
    if product == 'NCS6000' or 'r10' in hostname:
        logger.debug('r10 in hostname...')
        product_group = 'NCS 6000'
        product_model = 'NCS 6008'
        os = 'IOS XR'
        stats = (product_group, product_model, os)
    else:
        logger.debug('hostname did not provide enough info to generate product_stats.')
        product_group = 'TBD'
        product_model = 'TBD'
        os = 'TBD'
        stats = (product_group, product_model, os)
    logger.debug('product_stats set to %s' % str(stats))
    return stats

def customer_POC(product, hostname):
    logger = logging.getLogger('customer_tfs_data_normalization.customer_POC')
    if product == 'NCS6000' or 'r10' in hostname:
        POC = 'John Doe'
    else:
        POC = 'TBD'
    #logger.debug('customer_POC set to %s' % POC)
    return POC

def supplier_POC(product, hostname):
    logger = logging.getLogger('customer_tfs_data_normalization.supplier_POC')
    if product == 'NCS6000' or 'r10' in hostname:
        POC = 'John Doe'
    else:
        POC = 'TBD'
    logger.debug('supplier_POC set to %s' % POC)
    return POC

def product(raw_info, title):
    logger = logging.getLogger('customer_tfs_data_normalization.product')
    if raw_info in (u'panini', u'asr9k') or 'XR' in title:
        product = 'NCS6000'
    else:
        product = raw_info
    logger.debug('product set to %s' % product)
    return product

def found_in_version(raw_info):
    logger = logging.getLogger('customer_tfs_data_normalization.found_in_version')
    #really should poll NatKit for hostname to get this info.  Need to add this functionality.
    version = raw_info
    logger.debug('Found in version set to %s' % version)
    return version
    
def split_release(release):
    logger = logging.getLogger('customer_tfs_data_normalization.split_release')
    logger.info('Splitting IOS XR version %s...' % release)
    releaseList = release.split('.')
    _release_major = int(releaseList[0])
    _release_minor = int(releaseList[1])
    _release_external_build = int(releaseList[2])
    if 'i' in releaseList[3]:
        _release_internal_build = int(releaseList[3][:-1])
    else:
        _release_internal_build = releaseList[3]
    release = [_release_major, _release_minor, _release_external_build, _release_internal_build]
    if len(releaseList) == 5:
        _release_package = releaseList[4]
        release.append(_release_package)
    logger.debug('Split IOS XR image is %s' % str(release))
    return release

def fixed_in_releases(product, raw_info):
    logger = logging.getLogger('customer_tfs_data_normalization.fixed_in_releases')
    #Need to add more bust logic to this.  Probably an N and Nplus1 variables in the variables module.
    #then leverage those variables to check for integration into those releases.
    if product in ['NCS6000']:
        logger.debug('Checking to see if DDTS is in N+1 version for NCS6K...')    
        if product =='NCS6000':
            N_release = customer_account_variables.NCS6K_N_RELEASE
            Nplus1_release = customer_account_variables.NCS6K_Nplus1_RELEASE
        N_release = N_release.split('.')
        N_release_major = int(N_release[0])
        N_release_minor = int(N_release[1])
        N_release_external_build = int(N_release[2])        
        Nplus1_release = Nplus1_release.split('.')
        Nplus1_release_major = int(Nplus1_release[0])
        Nplus1_release_minor = int(Nplus1_release[1])
        Nplus1_release_external_build = int(Nplus1_release[2])
        majorNumbers = []
        for release in raw_info:
            _split_release = split_release(release)
            if len(_split_release) == 4:
                _release_major, _release_minor, _release_external_build, _release_internal_build = _split_release
            if len(_split_release) == 5:
                _release_major, _release_minor, _release_external_build, _release_internal_build, _release_package = _split_release
            logger.debug('_release_major=%s' % str(_release_major))
            if _release_major not in majorNumbers:
                majorNumbers.append(_release_major)
                logger.debug('majorNumbers=%s' % str(majorNumbers))
        majorNumbers.sort()
        logger.debug('Major Release Numbers in integrated releases field %s' % str(majorNumbers))
        for release in raw_info:
            _split_release = split_release(release)
            if len(_split_release) == 4:
                _release_major, _release_minor, _release_external_build, _release_internal_build = _split_release
            elif len(_split_release) == 5:
                _release_major, _release_minor, _release_external_build, _release_internal_build, _release_package = _split_release 
            else:
                logger.debug('Release version %s has an incorrect number of parts.' % release)
            logger.debug('Release split = %s' % str(_split_release))
            logger.debug('Checking release %s...' % release)
            _release_Nplus1 = False
            if Nplus1_release_major in majorNumbers:
                logger.debug('Nplus1_release_Major in majorNumbers.  Evaluating if Fixed is in N+1 release.')
                if _release_major == Nplus1_release_major:
                    logger.debug('_release_major=%s, Nplus1_release_major=%s' % (_release_major, Nplus1_release_major))
                    if _release_minor == Nplus1_release_minor and _release_external_build <= Nplus1_release_external_build:
                        logger.debug('_release_minor=%s, Nplus1_release_minor=%s' % (_release_major, Nplus1_release_major))
                        logger.debug('_release_external_build=%s, Nplus1_release_external_build=%s' % (_release_external_build, Nplus1_release_external_build))
                        if _release_external_build <= Nplus1_release_external_build:
                            logger.debug('_release_external_build=%s, Nplus1_release_external_build=%s)' % (_release_external_build, Nplus1_release_external_build))
                            release = customer_account_variables.NCS6K_Nplus1_RELEASE
                            logger.debug('Release is set to %s' % release)
                            if not _release_Nplus1:
                                _release_Nplus1 = True
                                logger.debug('fixed_in_releases set to %s' % release)
                                return release
                    elif _release_minor < Nplus1_release_minor:
                        logger.debug('_release_minor=%s, Nplus1_release_minor=%s' % (_release_minor, Nplus1_release_minor))
                        release = customer_account_variables.NCS6K_Nplus1_RELEASE
                        logger.debug('Release is set to %s' % release)
                        if not _release_Nplus1:
                            _release_Nplus1 = True
                            logger.debug('fixed_in_releases set to %s' % release)
                            return release
                elif _release_major < Nplus1_release_major:
                    release = customer_account_variables.NCS6K_Nplus1_RELEASE
                    logger.debug('Release is set to %s' % release)
                    if not _release_Nplus1:
                        _release_Nplus1 = True
                        logger.debug('fixed_in_releases set to %s' % release)
                        return release
            #N+1 major release number not in majorNumbers list so need to check if lesser version has fix
            if _release_major < Nplus1_release_major:
                release = customer_account_variables.NCS6K_Nplus1_RELEASE
                logger.debug('Release is set to %s' % release)
                if not _release_Nplus1:
                    _release_Nplus1 = True
                    logger.debug('fixed_in_releases set to %s' % release)
                    return release
            if not _release_Nplus1:
                release = raw_info        
    else:
        release = raw_info
    logger.debug('fixed_in_releases set to %s' % release)
    #release = raw_info
    return release