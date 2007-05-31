# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import os
import unittest
import stat

from zope.interface import implements

from bzrlib.errors import NoSuchFile, PermissionDenied

from twisted.cred.credentials import SSHPrivateKey
from twisted.cred.error import UnauthorizedLogin
from twisted.cred.portal import IRealm, Portal

from twisted.conch.error import ConchError
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.ssh.transport import SSHServerTransport
from twisted.conch.ssh import keys, userauth
from twisted.conch.ssh.common import getNS, NS

from twisted.python import failure
from twisted.python.util import sibpath

from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.authserver.client.twistedclient import TwistedAuthServer
from canonical.config import config
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.codehosting import sftponly
from canonical.codehosting.tests.test_acceptance import (
    SFTPTestCase, SSHKeyMixin, deferToThread)
from canonical.testing import TwistedLayer


class SFTPTests(SFTPTestCase):
    layer = TwistedLayer

    @deferToThread
    def _test_rmdir_branch(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Try to remove a branch directory, which is not allowed.
        e = self.assertRaises(PermissionDenied, transport.rmdir, 'foo')
        self.failUnless(
            "removing branch directory 'foo' is not allowed." in str(e), str(e))

        # The 'foo' directory is still listed.
        self.failUnlessEqual(['bar', 'foo'], sorted(transport.list_dir('.')))

    def test_rmdir_branch(self):
        return self._test_rmdir_branch()

    @deferToThread
    def _test_mkdir_toplevel_error(self):
        # You cannot create a top-level directory.
        transport = self.getTransport()
        e = self.assertRaises(PermissionDenied, transport.mkdir, 'foo')
        self.failUnless(
            "Branches must be inside a person or team directory." in str(e),
            str(e))

    def test_mkdir_toplevel_error(self):
        return self._test_mkdir_toplevel_error()

    @deferToThread
    def _test_mkdir_invalid_product_error(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = self.getTransport('~testuser')

        # You cannot create a product directory unless the product name is
        # registered in Launchpad.
        e = self.assertRaises(PermissionDenied,
                transport.mkdir, 'no-such-product')
        self.failUnless(
            "Directories directly under a user directory must be named after a "
            "product name registered in Launchpad" in str(e),
            str(e))

    def test_mkdir_invalid_product_error(self):
        return self._test_mkdir_invalid_product_error()

    @deferToThread
    def _test_mkdir_not_team_member_error(self):
        # You can't mkdir in a team directory unless you're a member of that
        # team (in fact, you can't even see the directory).
        transport = self.getTransport()
        e = self.assertRaises(NoSuchFile,
                transport.mkdir, '~not-my-team/mozilla-firefox')
        self.failUnless("~not-my-team" in str(e))

    def test_mkdir_not_team_member_error(self):
        return self._test_mkdir_not_team_member_error()

    @deferToThread
    def _test_mkdir_team_member(self):
        # You can mkdir in a team directory that you're a member of (so long as
        # it's a real product), though.
        transport = self.getTransport()
        transport.mkdir('~testteam/firefox')

        # Confirm the mkdir worked by using list_dir.
        self.failUnless('firefox' in transport.list_dir('~testteam'))

        # You can of course mkdir a branch, too
        transport.mkdir('~testteam/firefox/shiny-new-thing')
        self.failUnless(
            'shiny-new-thing' in transport.list_dir('~testteam/firefox'))
        transport.mkdir('~testteam/firefox/shiny-new-thing/.bzr')

    def test_mkdir_team_member(self):
        return self._test_mkdir_team_member()

    @deferToThread
    def _test_rename_directory_to_existing_directory_fails(self):
        # 'rename dir1 dir2' should fail if 'dir2' exists. Unfortunately, it
        # will only fail if they both contain files/directories.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir1/foo')
        transport.mkdir('branch/.bzr/dir2')
        transport.mkdir('branch/.bzr/dir2/bar')
        self.assertRaises(
            IOError, transport.rename, 'branch/.bzr/dir1', 'branch/.bzr/dir2')

    def test_rename_directory_to_existing_directory_fails(self):
        return self._test_rename_directory_to_existing_directory_fails()

    @deferToThread
    def _test_rename_directory_to_empty_directory_succeeds(self):
        # 'rename dir1 dir2' succeeds if 'dir2' is empty. Not sure we want this
        # behaviour, but it's worth documenting.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir2')
        transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
        self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))

    def test_rename_directory_to_existing_directory_fails(self):
        return self._test_rename_directory_to_empty_directory_succeeds()

    @deferToThread
    def _test_rename_directory_succeeds(self):
        # 'rename dir1 dir2' succeeds if 'dir2' doesn't exist.
        transport = self.getTransport('~testuser/+junk')
        transport.mkdir('branch')
        transport.mkdir('branch/.bzr')
        transport.mkdir('branch/.bzr/dir1')
        transport.mkdir('branch/.bzr/dir1/foo')
        transport.rename('branch/.bzr/dir1', 'branch/.bzr/dir2')
        self.assertEqual(['dir2'], transport.list_dir('branch/.bzr'))

    def test_rename_directory_success(self):
        return self._test_rename_directory_succeeds()


class MockRealm:
    """A mock realm for testing userauth.SSHUserAuthServer.

    This realm is not actually used in the course of testing, so calls to
    requestAvatar will raise an exception.
    """

    implements(IRealm)

    def requestAvatar(self, avatar, mind, *interfaces):
        raise NotImplementedError("This should not be called")


class MockSSHTransport(SSHServerTransport):
    """A mock SSH transport for testing userauth.SSHUserAuthServer.

    SSHUserAuthServer expects an SSH transport which has a factory attribute
    which in turn has a portal attribute. Because the portal is important for
    testing authentication, we need to be able to provide an interesting portal
    object to the SSHUserAuthServer.

    In addition, we want to be able to capture any packets sent over the
    transport.
    """

    class Factory:
        pass

    def __init__(self, portal):
        self.packets = []
        self.factory = self.Factory()
        self.factory.portal = portal

    def sendPacket(self, messageType, payload):
        self.packets.append((messageType, payload))


class UserAuthServerMixin:
    def setUp(self):
        self.portal = Portal(MockRealm())
        self.transport = MockSSHTransport(self.portal)
        self.user_auth = sftponly.SSHUserAuthServer(self.transport)


class TestUserAuthServer(UserAuthServerMixin, unittest.TestCase):

    def test_sendBanner(self):
        # sendBanner should send an SSH 'packet' with type MSG_USERAUTH_BANNER
        # and two fields. The first field is the message itself, and the second
        # is the language tag.
        #
        # sendBanner automatically adds a trailing newline, because openssh and
        # Twisted don't add one when displaying the banner.
        #
        # See RFC 4252, Section 5.4.
        message = u"test message"
        self.user_auth.sendBanner(message, language='en-US')
        [(messageType, payload)] = self.transport.packets
        self.assertEqual(messageType, userauth.MSG_USERAUTH_BANNER)
        bytes, language, empty = getNS(payload, 2)
        self.assertEqual(bytes.decode('UTF8'), message + '\r\n')
        self.assertEqual('en-US', language)
        self.assertEqual('', empty)

    def test_sendBannerUsesCRLF(self):
        # sendBanner should make sure that any line breaks in the message are
        # sent as CR LF pairs.
        #
        # See RFC 4252, Section 5.4.
        self.user_auth.sendBanner(u"test\nmessage")
        [(messageType, payload)] = self.transport.packets
        bytes, language, empty = getNS(payload, 2)
        self.assertEqual(bytes.decode('UTF8'), u"test\r\nmessage\r\n")

    def test_requestRaisesConchError(self):
        # ssh_USERAUTH_REQUEST should raise a ConchError if tryAuth returns
        # None. Added to catch a bug noticed by pyflakes.
        # Whitebox test.
        def mock_try_auth(kind, user, data):
            return None
        def mock_eb_bad_auth(reason):
            reason.trap(ConchError)
        tryAuth, self.user_auth.tryAuth = self.user_auth.tryAuth, mock_try_auth
        _ebBadAuth, self.user_auth._ebBadAuth = (self.user_auth._ebBadAuth,
                                                 mock_eb_bad_auth)
        self.user_auth.serviceStarted()
        try:
            packet = NS('jml') + NS('foo') + NS('public_key') + NS('data')
            self.user_auth.ssh_USERAUTH_REQUEST(packet)
        finally:
            self.user_auth.serviceStopped()
            self.user_auth.tryAuth = tryAuth
            self.user_auth._ebBadAuth = _ebBadAuth


class MockChecker(SSHPublicKeyDatabase):
    """A very simple public key checker which rejects all offered credentials.

    Used by TestAuthenticationErrorDisplay to test that errors raised by
    checkers are sent to SSH clients.
    """

    error_message = u'error message'

    def requestAvatarId(self, credentials):
        return failure.Failure(
            sftponly.UserDisplayedUnauthorizedLogin('error message'))


class TestAuthenticationErrorDisplay(UserAuthServerMixin, TrialTestCase):
    """Check that auth error information is passed through to the client.

    Normally, SSH servers provide minimal information on failed authentication.
    With Launchpad, much more user information is public, so it is helpful and
    not insecure to tell users why they failed to authenticate.

    SSH doesn't provide a standard way of doing this, but the
    MSG_USERAUTH_BANNER message is allowed and seems appropriate. See RFC 4252,
    Section 5.4 for more information.
    """

    layer = TwistedLayer

    def setUp(self):
        UserAuthServerMixin.setUp(self)
        self.portal.registerChecker(MockChecker())
        self.user_auth.serviceStarted()
        self.key_data = self._makeKey()

    def tearDown(self):
        self.user_auth.serviceStopped()

    def _makeKey(self):
        keydir = sibpath(__file__, 'keys')
        public_key = keys.getPublicKeyString(
            data=open(os.path.join(keydir,
                                   'ssh_host_key_rsa.pub'), 'rb').read())
        return chr(0) + NS('rsa') + NS(public_key)

    def test_loggedToBanner(self):
        # When there's an authentication failure, we display an informative
        # error message through the SSH authentication protocol 'banner'.
        d = self.user_auth.ssh_USERAUTH_REQUEST(
            NS('jml') + NS('') + NS('publickey') + self.key_data)

        def check(ignored):
            # Check that we received a BANNER, then a FAILURE.
            self.assertEqual(
                list(zip(*self.transport.packets)[0]),
                [userauth.MSG_USERAUTH_BANNER, userauth.MSG_USERAUTH_FAILURE])

            # Check that the banner message is informative.
            bytes, language, empty = getNS(self.transport.packets[0][1], 2)
            self.assertEqual(bytes.decode('UTF8'),
                             MockChecker.error_message + u'\r\n')
        return d.addCallback(check)

    def test_unsupportedAuthMethodNotLogged(self):
        # Trying various authentication methods is a part of the normal
        # operation of the SSH authentication protocol. We should not spam the
        # client with warnings about this, as whenever it becomes a problem, we
        # can rely on the SSH client itself to report it to the user.
        d = self.user_auth.ssh_USERAUTH_REQUEST(
            NS('jml') + NS('') + NS('none') + NS(''))

        def check(ignored):
            # Check that we received only a FAILRE.
            [(message_type, data)] = self.transport.packets
            self.assertEqual(message_type, userauth.MSG_USERAUTH_FAILURE)

        return d.addCallback(check)


class TestPublicKeyFromLaunchpadChecker(TrialTestCase, SSHKeyMixin):
    """Tests for the SFTP server authentication mechanism.

    PublicKeyFromLaunchpadChecker accepts the SSH authentication information
    and contacts the authserver to determine if the given details are valid.

    Any authentication errors are displayed back to the user via an SSH
    MSG_USERAUTH_BANNER message.
    """

    layer = TwistedLayer

    def setUp(self):
        self.authService = AuthserverService()
        self.authService.startService()
        self.authserver = TwistedAuthServer(config.codehosting.authserver)
        self.checker = sftponly.PublicKeyFromLaunchpadChecker(self.authserver)
        self.prepareTestUser()
        self.valid_login = 'testuser'
        self.public_key = self.getPublicKey()
        self.sigData = (
            NS('') + chr(userauth.MSG_USERAUTH_REQUEST)
            + NS(self.valid_login) + NS('none') + NS('publickey') + '\xff'
            + NS('ssh-dss') + NS(self.public_key))
        self.signature = keys.signData(self.getPrivateKey(), self.sigData)

    def tearDown(self):
        self.authService.stopService()

    def test_successful(self):
        # We should be able to login with the correct public and private
        # key-pair. This test exists primarily as a control to ensure our other
        # tests are checking the right error conditions.
        creds = SSHPrivateKey(self.valid_login, 'ssh-dss', self.public_key,
                              self.sigData, self.signature)
        d = self.checker.requestAvatarId(creds)
        return d.addCallback(self.assertEqual, self.valid_login)

    def assertLoginError(self, creds, error_message):
        """Assert that logging in with 'creds' fails with 'message'.

        :param creds: SSHPrivateKey credentials.
        :param error_message: String excepted to match the exception's message.
        :return: Deferred. You must return this from your test.
        """
        d = self.assertFailure(
            self.checker.requestAvatarId(creds),
            sftponly.UserDisplayedUnauthorizedLogin)
        d.addCallback(
            lambda exception: self.assertEqual(str(exception), error_message))
        return d

    def test_noSuchUser(self):
        # When someone signs in with a non-existent user, they should be told
        # that. The usual security issues don't apply here because the list of
        # Launchpad user names is public.
        creds = SSHPrivateKey('no-such-user', 'ssh-dss', self.public_key,
                              self.sigData, self.signature)
        return self.assertLoginError(
            creds, 'No such Launchpad account: no-such-user')

    def test_noKeys(self):
        # When you sign into an existing account with no SSH keys, the SFTP
        # server should inform you that the account has no keys.
        creds = SSHPrivateKey('lifeless', 'ssh-dss', self.public_key,
                              self.sigData, self.signature)
        return self.assertLoginError(
            creds,
            "Launchpad user %r doesn't have a registered SSH key" % 'lifeless')

    def test_wrongKey(self):
        # When you sign into an existing account using the wrong key, you
        # should *not* be informed of the wrong key. This is because SSH often
        # tries several keys as part of normal operation.

        # Cheat a little and also don't provide a valid signature. This is OK
        # because the "no matching public key" failure occurs before the
        # "bad signature" failure.
        creds = SSHPrivateKey(self.valid_login, 'ssh-dss', 'invalid key',
                              None, None)
        d = self.assertFailure(
            self.checker.requestAvatarId(creds),
            UnauthorizedLogin)
        d.addCallback(
            lambda exception:
            self.failIf(isinstance(exception,
                                   sftponly.UserDisplayedUnauthorizedLogin),
                        "Should not be a UserDisplayedUnauthorizedLogin"))
        return d


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
