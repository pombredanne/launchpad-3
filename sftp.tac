from supermirrorsftp import sftponly
from twisted.cred import portal
from twisted.conch.ssh import keys
from twisted.application import service, internet

authserverURL = 'http://localhost:8999/'
hostPublicKey = keys.getPublicKeyString(data=???)
hostPrivateKey = keys.getPrivateKeyObject(data=???)

# Configure the authentication
portal = portal.Portal(sftponly.Realm())
portal.registerChecker(sftponly.PublicKeyFromLaunchpadChecker(authserverURL))
sftpfactory = sftponly.Factory()
sftpfactory.portal = portal

# Configure it to listen on a port
application = service.Application('sftponly')
internet.TCPServer(5022, sftpfactory).setServiceParent(application)

