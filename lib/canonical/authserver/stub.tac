# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.application import service, internet
from twisted.web import server

from canonical.authserver.xmlrpc import UserDetailsResource
from canonical.authserver.stub import StubUserDetailsStorage


application = service.Application("authserver_test")
site = server.Site(UserDetailsResource(StubUserDetailsStorage()))
internet.TCPServer(9666, site).setServiceParent(application)

