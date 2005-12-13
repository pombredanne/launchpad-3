
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

    def createUser(self, loginID, sshaDigestedPassword, displayname,
                   emailAddresses):
        return self.proxy.callRemote('createUser', loginID,
                                     sshaDigestedPassword, displayname,
                                     emailAddresses)

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
        return self.proxy.callRemote('fetchProductID', productName)

    def createBranch(self, personID, productID, branchName):
        return self.proxy.callRemote('createBranch', personID, productID,
                                     branchName)
