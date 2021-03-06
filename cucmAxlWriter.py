#!/usr/bin/env python3.6
__version__ = '0.4'
__author__ = 'Christopher Phillips'

# import sys
import logging
import tempfile
import os.path
from ucAppConfig import ccmAppConfig
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import urllib3  # imported to disable the SAN warning for the cert
urllib3.disable_warnings(urllib3.exceptions.SubjectAltNameWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


cawLogger = logging.getLogger(__name__)
cawLogger.setLevel(logging.DEBUG)
handler = logging.FileHandler('writerDebug.log', mode='w')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - \
                                %(message)s')
handler.setFormatter(formatter)
cawLogger.addHandler(handler)
# cawLogger.addHandler(logging.StreamHandler(sys.stdout))
cawLogger.info("Begin cucmAxlWriter Info Logging")
cawLogger.debug("Begin cucmAxlWriter Debug Logging")


class cucmAxlWriter:
    # uses cucmAxlConfig to create factory and service for CUCM AXL Writing

    factory = ''
    service = ''

    def __init__(self):
        myCucmConfig = ccmAppConfig('ucm.cfg')

        zeeplogger = logging.getLogger('zeep.transports')
        zeeplogger.setLevel(logging.DEBUG)
        zeephandler = logging.FileHandler('zeepDebug.log', mode='w')
        zeephandler.setLevel(logging.DEBUG)
        zeepformatter = logging.Formatter('%(asctime)s - %(name)s - \
                            %(levelname)s - %(message)s')
        zeephandler.setFormatter(zeepformatter)
        zeeplogger.addHandler(zeephandler)
        zeeplogger.info("Begin zeep Logging")

        tempzeep = os.path.join(tempfile.gettempdir(), 'wsdlsqlite.db')
        cache = SqliteCache(path=tempzeep, timeout=60)
        transport = Transport(cache=cache)
        #client = Client(myCucmConfig.getwsdlFileName(), transport=transport)

        session = Session()
        if myCucmConfig.getAppVerify():
            cawLogger.info("Session Security ENABLED")
            session.verify = myCucmConfig.getAppCert()
        else:
            cawLogger.info("Session Security DISABLED")
            session.verify = myCucmConfig.getAppVerify()
        cawLogger.info("Session Created")
        session.auth = HTTPBasicAuth(myCucmConfig.getAppUsername(),
                                     myCucmConfig.getAppPassword())
        cawLogger.info("Auth Created")

        client = Client(wsdl=myCucmConfig.getwsdlFileName(),
                        transport=Transport(session=session))
        cawLogger.info("Client Created")

        self.factory = client.type_factory('ns0')
        cawLogger.info("Factory Created")

        self.service = client.create_service(
            "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
            myCucmConfig.getAppApiUrl())
        cawLogger.info("Service Created")

    def userGet(self, username):
        try:
            obtainedUser = self.service.getUser(userid=username)
            cawLogger.debug(obtainedUser)
            return obtainedUser
        except Exception as e:
            # If user does not exist
            cawLogger.debug("User NOT found. Error=%s", e)
            return False

    def userExists(self, username):
        try:
            self.userGet(username)
            return True
        except Exception as e:
            cawLogger.debug("User NOT found. Error=%s", e)
            return False

    def userAdd(self, username):
        # current users will be LDAP synced
        return False

    def userUpdate(self, username, extension, did, deviceList, pin,
                   partition='Internal PAR'):
        userGroups = ['Standard CTI Enabled',
                      'Standard CCM End Users',
                      'Standard CTI Allow Control of Phones supporting '
                      + 'Connected Xfer and conf',
                      'Standard CTI Allow Control of Phones supporting '
                      + 'Rollover Mode']
        result = self.service.updateUser(
                        userid=username,
                        selfService=did,
                        associatedDevices={'device': deviceList},
                        primaryExtension={'pattern': extension,
                                          'routePartitionName': partition},
                        associatedGroups={'userGroup': userGroups},
                        homeCluster='true',
                        imAndPresenceEnable='true',
                        enableUserToHostConferenceNow='true',
                        attendeesAccessCode='232323',
                        enableMobility='true')
        cawLogger.info("Update User Completed")
        cawLogger.debug(result)

    def userDelete(self, username):
        return True

    def lineGet(self, extension, partition='Internal PAR'):
        try:
            getLine = self.service.getLine(pattern=extension,
                                           routePartitionName=partition)
            cawLogger.info("getLine Completed")
            cawLogger.debug(getLine)
            return getLine
        except Exception as e:
            return False

    def lineExists(self, extension, partition='Internal PAR'):
        cawLogger.debug("lineExists Called")
        try:
            getLine = self.service.getLine(pattern=extension,
                                           routePartitionName=partition)
            cawLogger.debug(getLine)
            cawLogger.info("Line Exists")
            return True
        except Exception as e:
            return False

    def lineAdd(self, extension, firstname, lastname, device_pool, city,
                vm='True', vmProfileName="<None>", partition='Internal PAR',
                usage='Device', cfw_css='None'):
        if not self.lineExists(extension):
            try:
                # devCss = city+' International CSS'
                # TODO: How to change this based on other CSS changes
                # TODO: Make this a variables passed in to fix other problems
                fwdCss = cfw_css
                # lineCss = 'Class - International'
                vmConfig = {
                    'forwardToVoiceMail': vm,
                    'callingSearchSpaceName': fwdCss}
                nameString = firstname + " " + lastname

                addlinepackage = self.factory.XLine()
                addlinepackage.pattern = extension
                addlinepackage.usage = usage
                addlinepackage.routePartitionName = partition
                # addlinepackage.shareLineAppearanceCssName = lineCss
                addlinepackage.callForwardAll = {
                    'forwardToVoiceMail': 'False',
                    'callingSearchSpaceName': fwdCss
                    # 'secondaryCallingSearchSpaceName': lineCss
                    }
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
                addlinepackage.alertingName = nameString
                addlinepackage.asciiAlertingName = nameString
                addlinepackage.description = nameString
                addlinepackage.voiceMailProfileName = vmProfileName
                addlinepackage.shareLineAppearanceCssName = city

                cawLogger.info("Line Factory Completed")
                cawLogger.debug(addlinepackage)

                createdLine = self.service.addLine(addlinepackage)
                cawLogger.debug("Line Created")
                cawLogger.debug(createdLine)
                cawLogger.info("Add Line Completed")
            except Exception as e:
                cawLogger.debug("Add Line Error. Server error=%s", e)
                raise Exception("Line could not be added")
        else:
            raise Exception("Line already exists")

    def lineUpdate(self, e164extension, eprise_extension, country_code):
        result = self.service.updateLine(pattern=e164extension,
                                         e164AltNum={'numMask': eprise_extension,
                                                     'isUrgent': 'false',
                                                     'addLocalRoutePartition': 'true',
                                                     'routePartition': 'Internal PAR',
                                                     'advertiseGloballyIls': 'true'})
        cawLogger.info("lineUpdate Completed")
        cawLogger.debug(result)

    def lineDelete(self, extension, partition='Internal PAR'):
        try:
            result = self.service.removeLine(pattern=extension,
                                             routePartitionName=partition)
            cawLogger.info("Remove Line Completed")
            cawLogger.info(result)
        except Exception as e:
            cawLogger.info(e)

    def deviceGetName(self, username, devicetype):
        if devicetype == 'CSF':
            deviceName = 'CSF'+username
        elif devicetype == 'TCT':
            deviceName = 'TCT'+username
        elif devicetype == 'BOT':
            deviceName = 'BOT'+username
        elif devicetype == 'TAB':
            deviceName = 'TAB'+username

        deviceName = deviceName.upper()
        return deviceName

    def deviceGet(self, devicename):
        try:
            getDevice = self.service.getPhone(name=devicename)
            cawLogger.info("getDevice Completed")
            cawLogger.debug(getDevice)
            return getDevice
        except Exception as e:
            return False

    def deviceExists(self, devicename):
        try:
            getPhone = self.service.getPhone(name=devicename)
            cawLogger.info("getPhone Completed")
            cawLogger.debug(getPhone)
            return True
        except Exception as e:
            return False

    def deviceAdd(self, username, firstname, lastname, e164ext, extension, did,
                  device_pool, calling_search_space, devicetype, partition='Internal PAR'):

        nameString = firstname + " " + lastname
        nameDevicePool = device_pool
        deviceName = self.deviceGetName(username, devicetype)
        tempPhoneConfigName = 'Standard Common Phone Profile'
        devCss = calling_search_space

        if devicetype == 'CSF':
            tempProduct = 'Cisco Unified Client Services Framework'
            tempModel = 'Cisco Unified Client Services Framework'
        elif devicetype == 'TCT':
            tempProduct = 'Cisco Dual Mode for iPhone'
            tempModel = 'Cisco Dual Mode for iPhone'
        elif devicetype == 'BOT':
            tempProduct = 'Cisco Dual Mode for Android'
            tempModel = 'Cisco Dual Mode for Android'
        elif devicetype == 'TAB':
            tempProduct = 'Cisco Jabber for Tablet'
            tempModel = 'Cisco Jabber for Tablet'
        else:
            raise Exception("Invalid Device Type Specified, unrecoverable")

        if not self.deviceExists(deviceName):
            try:
                #  create device
                #  join line to device
                # directory number / line, required for a PhoneLine
                # line must allready exist
                tempDirN1 = self.factory.XDirn()
                tempDirN1.pattern = e164ext
                tempDirN1.routePartitionName = partition
                cawLogger.debug(tempDirN1)

                # PhoneLine is how a DirectoryNumber and a Phone are merged
                tempPhoneLine1 = self.factory.XPhoneLine()
                tempPhoneLine1.index = 1
                tempPhoneLine1.dirn = tempDirN1
                tempPhoneLine1.label = nameString + " " + extension
                tempPhoneLine1.display = nameString
                tempPhoneLine1.displayAscii = nameString
                # TODO: I think this is just the normal mask if that is so it needs to be removed
                # tempPhoneLine1.e164Mask = did

                tempPhoneLine1.associatedEndusers = {'enduser':
                                                     {'userId': username}}

                cawLogger.debug(tempPhoneLine1)

                addphonepackage = self.factory.XPhone()
                addphonepackage.name = deviceName
                addphonepackage.description = nameString + " x" + extension
                addphonepackage.product = tempProduct
                addphonepackage.model = tempModel
                addphonepackage['class'] = 'Phone'
                addphonepackage.protocol = 'SIP'
                addphonepackage.commonPhoneConfigName = tempPhoneConfigName
                addphonepackage.locationName = 'Hub_None'
                addphonepackage.devicePoolName = nameDevicePool
                addphonepackage.lines = {'line': tempPhoneLine1}
                addphonepackage.ownerUserName = username
                addphonepackage.mobilityUserIdName = username
                addphonepackage.callingSearchSpaceName = devCss
                cawLogger.debug(addphonepackage)

                createdPhone = self.service.addPhone(addphonepackage)
                cawLogger.debug(createdPhone)
                cawLogger.debug("Phone Created")
                cawLogger.info("Add Phone Completed")
            except Exception as e:
                cawLogger.debug("Add Phone Error. Server error=%s", e)
                # raise Exception("Phone could not be added")
                raise Exception(e)

    def deviceUpdate(self, username):
        return False

    def deviceDelete(self, username, devicetype):
        deviceName = self.deviceGetName(username, devicetype)
        try:
            result = self.service.removePhone(name=deviceName)
            cawLogger.info("Remove Phone Completed")
            cawLogger.info(result)
            return True
        except Exception as e:
            cawLogger.info(e)
            return False

    def rdpGet(self, name):
        try:
            getRdp = self.service.getRemoteDestinationProfile(name=name)
            cawLogger.info("getRdp Completed")
            cawLogger.debug(getRdp)
            return getRdp
        except Exception as e:
            return False

    def rdpExists(self, name):
        try:
            getRdp = self.service.getRemoteDestinationProfile(name=name)
            cawLogger.info("getRdp Completed")
            cawLogger.debug(getRdp)
            return True
        except Exception as e:
            return False

    def rdpAdd(self, username, firstname, lastname, e164ext, did, extension,
               device_pool, calling_search_space, partition='Internal PAR'):
        deviceName = "RDP"+username
        if not self.deviceExists(deviceName):
            try:
                nameString = firstname + " " + lastname

                tempDirN1 = self.factory.XDirn()
                tempDirN1.pattern = e164ext
                tempDirN1.routePartitionName = partition
                cawLogger.debug(tempDirN1)

                # XPhoneLine is how a DirectoryNumber and a Phone are merged
                tempPhoneLine1 = self.factory.XPhoneLine()
                tempPhoneLine1.index = 1
                tempPhoneLine1.dirn = tempDirN1

                cawLogger.debug(tempPhoneLine1)

                nameCss = calling_search_space
                nameDevicePool = device_pool

                rdpPackage = self.factory.XRemoteDestinationProfile()
                rdpPackage.name = deviceName
                rdpPackage.description = nameString + " x" + extension
                rdpPackage.product = 'Remote Destination Profile'
                rdpPackage.model = 'Remote Destination Profile'
                rdpPackage['class'] = 'Remote Destination Profile'
                rdpPackage.protocol = 'Remote Destination'
                rdpPackage.protocolSide = 'User'
                rdpPackage.callingSearchSpaceName = nameCss
                rdpPackage.devicePoolName = nameDevicePool
                rdpPackage.lines = {'line': tempPhoneLine1}
                rdpPackage.callInfoPrivacyStatus = 'Default'
                rdpPackage.userId = username
                rdpPackage.rerouteCallingSearchSpaceName = nameCss
                rdpPackage.primaryPhoneName = "CSF" + username

                result = self.service.addRemoteDestinationProfile(rdpPackage)
                return result
            except Exception as e:
                cawLogger.debug("Add Phone Error. Server error=%s", e)
                # raise Exception("Phone could not be added")
                # return "RDP Add Failed"
                return e

    def rdpUpdate(self, name):
        return False

    def rdpDelete(self, name):
        devName = "RDP"+name
        try:
            result = self.service.removeRemoteDestinationProfile(name=devName)
            cawLogger.info("Remove RDP Completed")
            cawLogger.info(result)
            return "Deleted"
        except Exception as e:
            cawLogger.info(e)
            return "NOT Deleted"

    def rDestGet(self, dest):
        try:
            getRDest = self.service.getRemoteDestination(destination=dest)
            print(getRDest)
            cawLogger.info("get Remote Dest Completed")
            cawLogger.debug(getRDest)
            return getRDest
        except Exception as e:
            return False

    def rDestExists(self, dest):
        try:
            getRDest = self.service.getRemoteDestination(destination=dest)
            print(getRDest)
            cawLogger.info("get Remote Dest Completed")
            cawLogger.debug(getRDest)
            return True
        except Exception as e:
            return False

    def rDestAdd(self, dest, userid, e164ext):
        '''Bug in 11.5 and earlier API will prevent this from working.
        In AXLSoap.xsd both dualModeDeviceName and
        remoteDestinationProfileName have a minOccurs value of 1
        yet these are mutually exclusive when configuring this device
        found notes here
        https://communities.cisco.com/thread/47106?start=0&tstart=0
        notes indicated
        "I had to edit the 10.5 AXLsoap.xsd file.  Under the
        XRemoteDestination -> dualModeDeviceName
        I set the minOccurs setting from 1 to 0.
        Now AXL schema doesn't inject this setting into the response and
        everything builds correctly.'''

        cawLogger.info("Remote Dest Add Started")
        devName = "RD"+userid
        try:
            rdPackage = self.factory.XRemoteDestination()
            # not required or unique
            rdPackage.name = devName
            # required AND unique
            rdPackage.destination = dest
            rdPackage.answerTooSoonTimer = 1500
            rdPackage.answerTooLateTimer = 19000
            rdPackage.delayBeforeRingingCell = 4000
            rdPackage.ownerUserId = userid
            rdPackage.remoteDestinationProfileName = "RDP" + userid
            rdPackage.isMobilePhone = 'true'
            rdPackage.enableMobileConnect = 'true'
            # rdPackage.dualModeDeviceName = "BOT" + userid
            print(rdPackage)

            result = self.service.addRemoteDestination(rdPackage)
            print(result)
            return result
        except Exception as e:
            cawLogger.debug("Add Remote Dest Error. Server error=%s", e)
            # raise Exception("Phone could not be added")
            # return "RDP Add Failed"
            return e

    def rDestUpdate(self):
        return False

    def rDestDelete(self):
        return False
