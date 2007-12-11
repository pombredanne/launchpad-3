
from twisted.web.xmlrpc import Proxy

class TwistedAuthServer:
    """Twisted client for the authserver.

    This almost implements canonical.authserver.interfaces.IUserDetailsStorage,
    except everything returns Deferreds.  Refer to IUserDetailsStorage for docs.
    """

    def __init__(self, url):
        self.proxy = Proxy(url)

    def getUser(self, loginID):
        return self.proxy.callRemote('getUser', loginID)

    def authUser(self, loginID, sshaDigestedPassword):
        return self.proxy.callRemote('authUser', loginID, sshaDigestedPassword)

    def changePassword(self, loginID, sshaDigestedPassword,
                       newSshaDigestedPassword):
        return self.proxy.callRemote('changePassword', loginID,
                                     sshaDigestedPassword,
                                     newSshaDigestedPassword)

    def getSSHKeys(self, archiveName):
        return self.proxy.callRemote('getSSHKeys', archiveName)

    def getBranchesForUser(self, personID):
        return self.proxy.callRemote('getBranchesForUser', personID)

    def fetchProductID(self, productName):
        d = self.proxy.callRemote('fetchProductID', productName)
        d.addCallback(self._cb_fetchProductID)
        return d

    def _cb_fetchProductID(self, productID):
        if productID == '':
            productID = None
        return productID

    def createBranch(self, loginID, personName, productName, branchName):
        return self.proxy.callRemote(
            'createBranch', loginID, personName, productName, branchName)

    def requestMirror(self, loginID, branchID):
        return self.proxy.callRemote('requestMirror', loginID, branchID)

