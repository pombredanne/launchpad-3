# Twisted Application Configuration file.
# Use with "twistd -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service, internet
from twisted.web import server

from canonical.launchpad.daemons.trebuchet import TrebuchetServer


# Construct the application
application = service.Application("trebuchet")

# Construct the server
treb = TrebuchetServer()

# Create the server and tie the service to the application
internet.TCPServer(4280, server.Site(treb)).setServiceParent(application)
