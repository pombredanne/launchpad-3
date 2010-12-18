# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service

from canonical.config import config
from canonical.launchpad.daemons import readyservice

from lp.codehosting.sshserver.daemon import (
    ACCESS_LOG_NAME, get_key_path, LOG_NAME, make_portal, OOPS_CONFIG_SECTION,
    PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
from lp.services.sshserver.service import SSHService


# Construct an Application that has the codehosting SSH server.
application = service.Application('sftponly')
svc = SSHService(
    portal=make_portal(),
    private_key_path=get_key_path(PRIVATE_KEY_FILE),
    public_key_path=get_key_path(PUBLIC_KEY_FILE),
    oops_configuration=OOPS_CONFIG_SECTION,
    main_log=LOG_NAME,
    access_log=ACCESS_LOG_NAME,
    access_log_path=config.codehosting.access_log,
    strport=config.codehosting.port,
    idle_timeout=config.codehosting.idle_timeout,
    banner=config.codehosting.banner)
svc.setServiceParent(application)

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(application)
