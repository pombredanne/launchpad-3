# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service

from canonical.launchpad.daemons import tachandler
from lp.codehosting.sshserver.service import (
    get_key_path, make_portal, PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, SSHService)


# Construct an Application that has the codehosting SSH server.
application = service.Application('sftponly')
svc = SSHService(
    portal=make_portal(),
    private_key_path=get_key_path(PRIVATE_KEY_FILE),
    public_key_path=get_key_path(PUBLIC_KEY_FILE))
svc.setServiceParent(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(application)
