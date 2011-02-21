# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

import os

from twisted.application import service, strports
from twisted.conch.interfaces import ISession
from twisted.conch.ssh import filetransfer
from twisted.cred.portal import IRealm, Portal
from twisted.protocols import ftp
from twisted.protocols.policies import TimeoutFactory
from twisted.python import components
from twisted.web.xmlrpc import Proxy

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.daemons import readyservice

from lp.poppy.twistedftp import (
    FTPRealm,
    PoppyAccessCheck,
    )
from lp.poppy.twistedsftp import SFTPServer
from lp.services.sshserver.auth import (
    LaunchpadAvatar, PublicKeyFromLaunchpadChecker)
from lp.services.sshserver.service import SSHService
from lp.services.sshserver.session import DoNothingSession

# XXX: Rename this file to something that doesn't mention poppy. Talk to
# bigjools.


def make_portal():
    """Create and return a `Portal` for the SSH service.

    This portal accepts SSH credentials and returns our customized SSH
    avatars (see `LaunchpadAvatar`).
    """
    authentication_proxy = Proxy(
        config.poppy.authentication_endpoint)
    portal = Portal(Realm(authentication_proxy))
    portal.registerChecker(
        PublicKeyFromLaunchpadChecker(authentication_proxy))
    return portal


class Realm:
    implements(IRealm)

    def __init__(self, authentication_proxy):
        self.authentication_proxy = authentication_proxy

    def requestAvatar(self, avatar_id, mind, *interfaces):
        # Fetch the user's details from the authserver
        deferred = mind.lookupUserDetails(
            self.authentication_proxy, avatar_id)

        # Once all those details are retrieved, we can construct the avatar.
        def got_user_dict(user_dict):
            avatar = LaunchpadAvatar(user_dict)
            return interfaces[0], avatar, avatar.logout

        return deferred.addCallback(got_user_dict)


def get_poppy_root():
    """Return the poppy root to use for this server.

    If the POPPY_ROOT environment variable is set, use that. If not, use
    config.poppy.fsroot.
    """
    poppy_root = os.environ.get('POPPY_ROOT', None)
    if poppy_root:
        return poppy_root
    return config.poppy.fsroot


def poppy_sftp_adapter(avatar):
    return SFTPServer(avatar, get_poppy_root())


components.registerAdapter(
    poppy_sftp_adapter, LaunchpadAvatar, filetransfer.ISFTPServer)

components.registerAdapter(DoNothingSession, LaunchpadAvatar, ISession)


class FTPServiceFactory(service.Service):
    def __init__(self, port):
        factory = ftp.FTPFactory()
        realm = FTPRealm(get_poppy_root())
        portal = Portal(realm)
        portal.registerChecker(PoppyAccessCheck())

        factory.tld = get_poppy_root()
        factory.portal = portal
        factory.protocol = ftp.FTP
        factory.welcomeMessage = "Launchpad upload server"
        factory.timeOut = config.poppy.idle_timeout

        # Setting this works around the fact that the twistd FTP server
        # invokes a special restricted shell when someone logs in as
        # "anonymous" which is the default for 'dput'.
        factory.userAnonymous = "userthatwillneverhappen"
        self.ftpfactory = factory
        self.portno = port

    @staticmethod
    def makeFTPService(port=2121):
        strport = "tcp:%s" % port
        factory = FTPServiceFactory(port)
        return strports.service(strport, factory.ftpfactory)

# ftpport defaults to 2121 in schema-lazr.conf
ftpservice = FTPServiceFactory.makeFTPService(port=config.poppy.ftpport)

# Construct an Application that has the Poppy SSH server,
# and the Poppy FTP server.
application = service.Application('poppy-sftp')

ftpservice.setServiceParent(application)

def timeout_decorator(factory):
    """Add idle timeouts to a factory."""
    return TimeoutFactory(factory, timeoutPeriod=config.poppy.idle_timeout)

svc = SSHService(
    portal=make_portal(),
    private_key_path=config.poppy.host_key_private,
    public_key_path=config.poppy.host_key_public,
    oops_configuration='poppy',
    main_log='poppy',
    access_log='poppy.access',
    access_log_path=config.poppy.access_log,
    strport=config.poppy.port,
    factory_decorator=timeout_decorator,
    banner=config.poppy.banner)
svc.setServiceParent(application)

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(application)
