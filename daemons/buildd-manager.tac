# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service
from twisted.scripts.twistd import ServerOptions
from twisted.web import server

from lp.buildmaster.manager import BuilddManager
from lp.services.twistedsupport.loggingsupport import RotatableFileLogObserver
from canonical.config import config
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.launchpad.daemons import readyservice
from canonical.launchpad.scripts import execute_zcml_for_scripts

execute_zcml_for_scripts()
ZopelessTransactionManager.initZopeless(dbuser=config.builddmaster.dbuser)

options = ServerOptions()
options.parseOptions()

application = service.Application('BuilddManager')
application.addComponent(
    RotatableFileLogObserver(options.get('logfile')), ignoreClass=1)

# Service that announces when the daemon is ready.
readyservice.ReadyService().setServiceParent(application)

# Service for scanning buildd slaves.
service = BuilddManager()
service.setServiceParent(application)

