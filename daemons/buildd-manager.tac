# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service
from twisted.web import server

from canonical.buildmaster.manager import BuilddManager
from canonical.config import config
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless

execute_zcml_for_scripts()
initZopeless(dbuser=config.builddmaster.dbuser)

application = service.Application('BuilddManager')
service = BuilddManager()
service.setServiceParent(application)
