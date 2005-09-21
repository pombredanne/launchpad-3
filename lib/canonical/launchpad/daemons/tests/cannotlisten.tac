# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""
This TAC is used for the TacTestSetupTestCase.test_couldNotListenTac test case
in test_tachandler.py.  It fails with a CannotListenError.
"""

__metaclass__ = type

from twisted.application import service, internet, strports
from twisted.internet import protocol

from canonical.launchpad.daemons import tachandler


application = service.Application('CannotListen')
serviceCollection = service.IServiceCollection(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(serviceCollection)

# We almost certainly can't listen on port 1 (usually it requires root
# permissions), so this should fail.
internet.TCPServer(1, protocol.Factory()).setServiceParent(serviceCollection)

# Just in case we can, try listening on port 1 *again*.  This will fail.
internet.TCPServer(1, protocol.Factory()).setServiceParent(serviceCollection)

