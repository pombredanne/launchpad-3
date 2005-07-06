# Twisted Application Configuration file.
# Use with "twistd -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service, internet
from twisted.web import server

from canonical.launchpad.daemons.trebuchet import TrebuchetServer
from canonical.lp import initZopeless
from canonical.config import config


# Connect to database
# (hctapi will pick this up automatically)
initZopeless(dbuser=config.trebuchet.dbuser, implicitBegin=False)

# Construct the application
application = service.Application("trebuchet")

# Construct the server
treb = TrebuchetServer()

# Create the server and tie the service to the application
tcpPort = int(config.trebuchet.port)
internet.TCPServer(tcpPort, server.Site(treb)).setServiceParent(application)
