# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
#
# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service

from canonical.launchpad.daemons import tachandler
from canonical.launchpad.daemons.sftp import SSHService


# Construct an Application that includes a supermirror SFTP service. 
application = service.Application('sftponly')
svc = SSHService()
svc.setServiceParent(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(application)
