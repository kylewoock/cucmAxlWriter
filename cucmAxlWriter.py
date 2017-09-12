#!/usr/bin/env python3.6
__version__ = '0.4'
__author__ = 'Christopher Phillips'

import logging
from cucmAxlConfig import cucmAxlConfig
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import urllib3  # imported to disable the SAN warning for the cert
urllib3.disable_warnings(urllib3.exceptions.SubjectAltNameWarning)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('writerDebug.log', mode='w')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - \
                                %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Begin cucmAxlWriter Info Logging")
logger.debug("Begin cucmAxlWriter Debug Logging")


class cucmAxlWriter:
    # uses cucmAxlConfig to create factory and service for CUCM AXL Writing

    factory = ''
    service = ''

    def __init__(self):
        myCucmConfig = cucmAxlConfig()

        logger.debug("current CUCM username is %s",
                     myCucmConfig.getCucmUsername())
        logger.debug("current CUCM password is %s",
                     myCucmConfig.getCucmPassword())
        logger.debug("current CUCM url is %s", myCucmConfig.getCucmUrl())
        logger.debug("current CUCM axlurl is %s", myCucmConfig.getCucmAxlUrl())
        logger.debug("current CUCM verify mode is %s",
                     myCucmConfig.getCucmVerify())
        logger.debug("current CUCM Cert File  is %s",
                     myCucmConfig.getCucmCert())

        zeeplogger = logging.getLogger('zeep.transports')
        zeeplogger.setLevel(logging.DEBUG)
        zeephandler = logging.FileHandler('zeepDebug.log', mode='w')
        zeephandler.setLevel(logging.DEBUG)
        zeepformatter = logging.Formatter('%(asctime)s - %(name)s - \
                            %(levelname)s - %(message)s')
        zeephandler.setFormatter(zeepformatter)
        zeeplogger.addHandler(zeephandler)
        zeeplogger.info("Begin zeep Logging")

        cache = SqliteCache(path='/tmp/wsdlsqlite.db', timeout=60)
        transport = Transport(cache=cache)
        client = Client(myCucmConfig.getwsdlFileName(), transport=transport)

        session = Session()
        if myCucmConfig.getCucmVerify():
            logger.info("Session Security ENABLED")
            session.verify = myCucmConfig.getCucmCert()
        else:
            logger.info("Session Security DISABLED")
            session.verify = myCucmConfig.getCucmVerify()
        logger.info("Session Created")
        session.auth = HTTPBasicAuth(myCucmConfig.getCucmUsername(),
                                     myCucmConfig.getCucmPassword())
        logger.info("Auth Created")

        client = Client(wsdl=myCucmConfig.getwsdlFileName(),
                        transport=Transport(session=session))
        logger.info("Client Created")

        self.factory = client.type_factory('ns0')
        logger.info("Factory Created")

        self.service = client.create_service(
            "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
            myCucmConfig.getCucmAxlUrl())
        logger.info("Service Created")

    # TODO LDAP
        # check LDAP sync time (can this be checked?)
        # GetLdapDirectoryReq ?
        # getLdapSyncCustomField ?
        # getLdapSyncCustomFieldResponse ?
        # GetLdapSyncStatusReq !
        # TODO   kick off LDAP Sync (maybe just do this always)
        # TODO   Check LDAP sync time again?

    def userGet(self, username):
        try:
            obtainedUser = self.service.getUser(userid=username)
            logger.debug(obtainedUser)
            return obtainedUser
        except Exception as e:
            # If user does not exist
            logger.debug("User NOT found. Error=%s", e)
            return False

    def userExists(self, username):
        try:
            self.userGet(username)
            return True
        except Exception as e:
            logger.debug("User NOT found. Error=%s", e)
            return False

    def userAdd(self, username):
        # TODO : build for future if needed
        # current users will be LDAP synced
        return False

    def userUpdate(self, username, extension, partition='Phones'):
        deviceName = 'CSF'+username
        result = self.service.updateUser(
                        userid=username,
                        associatedDevices={'device': deviceName},
                        primaryExtension={'pattern': extension,
                                          'routePartitionName': partition})
        logger.info("Update User Completed")
        logger.debug(result)

    def userDelete(self, username):
        return True

    def lineGet(self, extension, partition='Phones'):
        try:
            getLine = self.service.getLine(pattern=extension,
                                           routePartitionName=partition)
            logger.info("getLine Completed")
            logger.debug(getLine)
            return getLine
        except Exception as e:
            return False

    def lineExists(self, extension, partition='Phones'):
        try:
            self.lineGet(extension, partition)
            return True
        except Exception as e:
            return False

    def lineAdd(self, extension, firstname, lastname, vm='False',
                partition='Phones', usage='Device'):
        if not self.lineExists(extension):
            try:
                vmCss = 'Device - Seattle'
                fwdAllCss = 'Device - Seattle'
                vmConfig = {
                    'forwardToVoiceMail': vm,
                    'callingSearchSpaceName': vmCss}
                nameString = firstname + " " + lastname

                addlinepackage = self.factory.XLine()
                addlinepackage.pattern = extension
                addlinepackage.usage = usage
                addlinepackage.routePartitionName = partition
                addlinepackage.callForwardAll = {
                    'forwardToVoiceMail': 'False',
                    'callingSearchSpaceName': vmCss,
                    'secondaryCallingSearchSpaceName': fwdAllCss}
                addlinepackage.callForwardBusy = vmConfig
                addlinepackage.callForwardBusyInt = vmConfig
                addlinepackage.callForwardNoAnswer = vmConfig
                addlinepackage.callForwardNoAnswerInt = vmConfig
                addlinepackage.callForwardNoCoverage = vmConfig
                addlinepackage.callForwardNoCoverageInt = vmConfig
                addlinepackage.callForwardOnFailure = vmConfig
                addlinepackage.callForwardAlternateParty = vmConfig
                addlinepackage.callForwardNotRegistered = vmConfig
                addlinepackage.callForwardNotRegisteredInt = vmConfig
                # addlinepackage.voiceMailProfileName = vmProfileName
                addlinepackage.addlinepackage.alertingName = nameString
                addlinepackage.asciiAlertingName = nameString
                '''
                'e164AltNum': {
                    'numMask': None,
                    'isUrgent': 'f',
                    'addLocalRoutePartition': 'f',
                    'routePartition': {
                        '_value_1': None,
                        'uuid': None
                    },
                    'advertiseGloballyIls': 'f'
                },
                '''

                logger.info("Line Factory Completed")
                logger.debug(addlinepackage)

                createdLine = self.service.addLine(addlinepackage)
                logger.debug("Line Created")
                logger.debug(createdLine)
                logger.info("Add Line Completed")
            except Exception as e:
                logger.debug("Add Line Error. Server error=%s", e)
                raise Exception("Line could not be added")
        else:
            raise Exception("Line already exists")

    def lineUpdate(self, extension):
        return True

    def lineDelete(self, extension, partition='Phones'):
        try:
            result = self.service.removeLine(pattern=extension,
                                             routePartitionName=partition)
            logging.info("Remove Line Completed")
            logging.info(result)
        except Exception as e:
            logging.info(e)

    def deviceExists(self, username):
        try:
            getPhone = self.service.getPhone(name='CSF'+username)
            logger.info("getPhone Completed")
            logger.debug(getPhone)
            return True
        except Exception as e:
            return False

    def deviceAdd(self, username, extension, site, partition='Phones'):
        deviceName = 'CSF'+username
        if not self.deviceExists(deviceName):
            try:
                tempProduct = 'Cisco Unified Client Services Framework'
                tempModel = 'Cisco Unified Client Services Framework'
                tempPhoneConfigName = 'Standard Common Phone Profile'
                #  create device
                #  join line to device
                # directory number / line, required for a PhoneLine
                # line must allready exist
                tempDirN1 = self.factory.XDirn()
                tempDirN1.pattern = extension
                tempDirN1.routePartitionName = partition
                logger.debug(tempDirN1)

                # PhoneLine is how a DirectoryNumber and a Phone are merged
                tempPhoneLine1 = self.factory.XPhoneLine()
                tempPhoneLine1.index = 1
                tempPhoneLine1.dirn = tempDirN1
                logger.debug(tempPhoneLine1)

                addphonepackage = self.factory.XPhone()
                addphonepackage.name = deviceName
                addphonepackage.product = tempProduct
                addphonepackage.model = tempModel
                addphonepackage['class'] = 'Phone'
                addphonepackage.protocol = 'SIP'
                addphonepackage.commonPhoneConfigName = tempPhoneConfigName
                addphonepackage.locationName = 'Hub_None'
                addphonepackage.devicePoolName = site
                addphonepackage.lines = {'line': tempPhoneLine1}
                addphonepackage.ownerUserName = username
                addphonepackage.callingSearchSpaceName = 'Device - ' + site
                logger.debug(addphonepackage)

                createdPhone = self.service.addPhone(addphonepackage)
                logger.debug(createdPhone)
                logger.debug("Phone Created")
                logger.info("Add Phone Completed")
            except Exception as e:
                logger.debug("Add Phone Error. Server error=%s", e)
                # raise Exception("Phone could not be added")
                raise Exception(e)

    def deviceUpdate(self, username):
        return True

    def deviceDelete(self, username):
        try:
            result = self.service.removePhone(name='CSF' + username)
            logging.info("Remove Phone Completed")
            logging.info(result)
        except Exception as e:
            logging.info(e)
