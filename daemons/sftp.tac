# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service

from canonical.launchpad.daemons import tachandler
from lp.codehosting.sshserver.service import SSHService


# Construct an Application that includes a supermirror SFTP service. 
application = service.Application('sftponly')
svc = SSHService()
svc.setServiceParent(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(application)
