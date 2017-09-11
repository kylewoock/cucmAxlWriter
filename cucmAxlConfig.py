#!/usr/bin/env python3.6
# cucmAxlConfig.py
__version__ = '0.4'
__author__ = 'Christopher Phillips'

import os  # directories
import logging  # debug
import json  # config file read/write

import socket  # download ssl cert, check IP vs hostname
import ssl  # download ssl cert
import OpenSSL  # download ssl cert

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create a file handler
handler = logging.FileHandler('configDebug.log', mode='w')
handler.setLevel(logging.DEBUG)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - \
                                %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(handler)
logger.info('Begin cucmAxlConfig Logging')


class cucmAxlConfig:
    # holds config data for CUCM
    def __init__(self):
        # default /axlsqltoolkit/schema/current/AXLAPI.wsdl
        self.__wsdlFileName = '/axlsqltoolkit/schema/10.5/AXLAPI.wsdl'
        # default /ucm.cfg
        self.__cucmCfgFileName = '/ucm.cfg'
        self.__cucmCertFileName = ''
        self.__cucmUrl = ''
        self.__cucmUsername = ''
        self.__cucmPassword = ''
        self.__cucmVerify = ''
        self.__localDir = os.getcwd()
        self.factory = ''
        self.service = ''

        wsdlFileFound = self.checkFileExists(self.__wsdlFileName,
                                             self.__localDir)
        if not wsdlFileFound:
            logger.error("This version of cucmAxlWriter is expecting" +
                         " the UCM 11.5 WSDL file.")
            logger.error("If you choose to use a different version of" +
                         "the WSDL your results may vary.")
            logger.error("The 11.5 version WSDL file must be placed in %s",
                         os.path.join(self.__localDir+self.__wsdlFileName))
            raise Exception('WSDL File NOT found. Unrecoverable error.')
        else:
            self.__wsdlFileName = self.__localDir + self.__wsdlFileName

        cucmCfgFileFound = self.checkFileExists(self.__cucmCfgFileName,
                                                self.__localDir)
        if not cucmCfgFileFound:
            print("The CUCM Cfg file was not found.")
            print("Generating a new config file.")
            self.__buildCucmCfgFile()
        self.__cucmCfgFileName = self.__localDir + self.__cucmCfgFileName
        self.__loadCucmCfgFile(self.__cucmCfgFileName)

        from zeep import Client
        from zeep.cache import SqliteCache
        from zeep.transports import Transport
        zeeplogger = logging.getLogger('zeep.transports')
        zeeplogger.setLevel(logging.DEBUG)
        zeephandler = logging.FileHandler('zeepDebug.log', mode='w')
        zeephandler.setLevel(logging.DEBUG)
        # create a logging format
        zeepformatter = logging.Formatter('%(asctime)s - %(name)s - \
                            %(levelname)s - %(message)s')
        zeephandler.setFormatter(zeepformatter)
        # add the handlers to the logger
        zeeplogger.addHandler(zeephandler)
        zeeplogger.info('Begin zeep Logging')

        cache = SqliteCache(path='/tmp/wsdlsqlite.db', timeout=60)
        transport = Transport(cache=cache)
        client = Client(self.getwsdlFileName(), transport=transport)

        from requests import Session
        from requests.auth import HTTPBasicAuth

        session = Session()
        if self.getCucmVerify():
            logger.info("Session Security ENABLED")
            session.verify = self.getCucmCert()
        else:
            logger.info("Session Security DISABLED")
            session.verify = self.getCucmVerify()
        logger.info("Session Created")
        session.auth = HTTPBasicAuth(self.getCucmUsername(),
                                     self.getCucmPassword())
        logger.info("Auth Created")

        client = Client(wsdl=self.getwsdlFileName(),
                        transport=Transport(session=session))
        logger.info("Client Created")

        self.factory = client.type_factory('ns0')
        logger.info("Factory Created")

        self.service = client.create_service(
            "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
            self.getCucmAxlUrl())
        logger.info("Service Created")

    def checkFileExists(self, filename, directory):
        if directory not in filename:
            fileLocation = directory + filename
        else:
            fileLocation = filename
        logger.debug("Checking for %s file in %s", filename, directory)
        fileExists = os.path.isfile(fileLocation)
        logger.debug("Exists=%s", fileExists)
        if not fileExists:
            logger.debug("%s NOT Found", fileLocation)
            return fileExists
        logger.debug("%s file found", filename)
        return fileExists

    def getwsdlFileName(self):
        return self.__wsdlFileName

    def getCucmUsername(self):
        return self.__cucmUsername

    def __setCucmUsername(self, username):
        self.__cucmUsername = username

    def getCucmPassword(self):
        return self.__cucmPassword

    def __setCucmPassword(self, password):
        self.__cucmPassword = password

    def getCucmUrl(self):
        return self.__cucmUrl

    def getCucmAxlUrl(self):
        return 'https://{0}:8443/axl/'.format(self.__cucmUrl)

    def __setCucmUrl(self, ipOrHostname):
        self.__cucmUrl = ipOrHostname

    def getCucmVerify(self):
        return self.__cucmVerify

    def __setCucmVerify(self, verify):
        self.__cucmVerify = verify
        if self.getCucmVerify():
            certFileExists = self.checkFileExists(self.__cucmCertFileName,
                                                  self.__localDir)
            if not certFileExists:
                self.__downloadCucmCert()

    def getCucmCert(self):
        return self.__cucmCertFileName

    def __downloadCucmCert(self):
        hostname = self.getCucmUrl()
        port = 443
        logger.debug("using %s:%s to download cert", hostname, port)
        cert = ssl.get_server_certificate((hostname, port))
        x509 = OpenSSL.crypto.load_certificate(
                                            OpenSSL.crypto.FILETYPE_PEM, cert)
        certExport = OpenSSL.crypto.dump_certificate(
                                            OpenSSL.crypto.FILETYPE_PEM, x509)
        certFileName = os.path.join(self.__localDir,
                                    '{0}.pem'.format(hostname))
        with open(certFileName, 'wb') as certFile:
            certFile.write(certExport)
            logger.debug("Cert file saved to %s", certFileName)
        self.__setCucmCert(certFileName)

    def __setCucmCert(self, certFileName):
        self.__cucmCertFileName = certFileName

    def getCucmCfgFileName(self):
        return self.__cucmCfgFileName

    def __loadCucmCfgFile(self, filename):
        logger.debug("Reading from file")
        try:
            with open(filename) as cucmCfgFile:
                cucmCfg = json.load(cucmCfgFile)
                self.__setCucmUsername(cucmCfg['username'])
                self.__setCucmPassword(cucmCfg['password'])
                self.__setCucmUrl(cucmCfg['url'])
                self.__setCucmVerify(cucmCfg['verify'])
                self.__setCucmCert(cucmCfg['verifyFile'])
                logger.debug("File Read successfully")
        except Exception as e:
            logger.debug("Unable to open Config file")
            os.remove(self.getCucmCfgFileName())

    def __buildCucmCfgFile(self):
        logger.debug("Building new config file")

        # TODO: Try block for sanitization
        username = input("UCM AXL Username: ")

        # TODO: Try block for sanitization
        password = input("UCM Password: ")

        print("NOTE: Certificates cannot be used if an IP Address is provided")
        # TODO: Try block for sanitization
        url = input("UCM hostname or IP Address: ")
        self.__setCucmUrl(url)  # temp workaround so cert download will work
        # consider refactoring

        # check if valid IP address by borrowing from socket
        try:
            socket.inet_aton(url)
            logger.debug("Bypassing certificate download")
            verify = False
        except socket.error:
            # TODO: Try block for sanitization
            verify = input("Use Certificates (y/n): ")
            if verify == 'y':
                logger.debug("Downloading certificate")
                self.__downloadCucmCert()
                certFileExists = self.checkFileExists(self.getCucmCert(),
                                                      self.__localDir)
                if certFileExists:
                    verify = True
                else:
                    verify = False
            else:
                logger.debug("Bypassing certificate download")
                verify = False

        data = {'username': username, 'password': password, 'url': url,
                'verify': verify, 'verifyFile': self.getCucmCert()}
        with open('ucm.cfg', 'w') as outfile:
            json.dump(data, outfile, ensure_ascii=False)
