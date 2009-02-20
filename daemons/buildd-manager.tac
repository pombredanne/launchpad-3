# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service
from twisted.web import server

from canonical.config import config, dbconfig
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.builddmanager import BuilddManager

# Connect to database
dbconfig.setConfigSection('builddmaster')
execute_zcml_for_scripts()

application = service.Application('BuilddManager')
service = BuilddManager()
service.setServiceParent(application)
