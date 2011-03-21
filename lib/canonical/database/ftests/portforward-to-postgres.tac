# -*- mode: python -*-

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

from twisted.application import service, internet
from twisted.protocols import portforward
from twisted.application.internet import TCPServer

import canonical.lp
from canonical.launchpad.daemons.readyservice import ReadyService

application = service.Application('portforward_to_postgres')

# The libpq library uses the $PGHOST environment variable as the
# default database host to connect to.  Fall back to
# canonical.lp.dbhost and then localhost.
if os.environ.get('PGHOST'):
    dbhost = os.environ.get('PGHOST')
elif canonical.lp.dbhost:
    dbhost = canonical.lp.dbhost
else:
    dbhost = 'localhost'

port = 5432
if os.environ.get('PGPORT'):
    port = int(os.environ.get('PGPORT'))

pf = portforward.ProxyFactory(dbhost, port)
svc = internet.TCPServer(5555, pf)
svc.setServiceParent(application)

ReadyService().setServiceParent(application)
