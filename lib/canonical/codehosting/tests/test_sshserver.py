import os
import unittest

from zope.interface import implements

from twisted.cred.credentials import SSHPrivateKey
from twisted.cred.error import UnauthorizedLogin
from twisted.cred.portal import IRealm, Portal

from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.error import ConchError
from twisted.conch.ssh import keys, userauth
from twisted.conch.ssh.common import getNS, NS
from twisted.conch.ssh.transport import SSHCiphers, SSHServerTransport

from twisted.python import failure
from twisted.python.util import sibpath

from twisted.trial.unittest import TestCase as TrialTestCase

from canonical.authserver.client.twistedclient import TwistedAuthServer
from canonical.codehosting import sshserver
from canonical.codehosting.tests.servers import AuthserverWithKeysInProcess
from canonical.config import config
from canonical.launchpad.daemons.sftp import getPublicKeyString
from canonical.testing.layers import TwistedLaunchpadZopelessLayer


class MockRealm:
    """A mock realm for testing userauth.SSHUserAuthServer.

    This realm is not actually used in the course of testing, so calls to
    requestAvatar will raise an exception.
    """

    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        user_dict = {
            'id': avatarId, 'name': avatarId, 'teams': [],
            'initialBranches': []}
        return (
            interfaces[0],
            sshserver.LaunchpadAvatar(avatarId, None, user_dict, None),
            lambda: None)


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
        def getService(self, transport, nextService):
            return lambda: None

    def __init__(self, portal):
        self.currentEncryptions = SSHCiphers('none', 'none', 'none', 'none')
        self.packets = []
        self.factory = self.Factory()
        self.factory.portal = portal

    def sendPacket(self, messageType, payload):
        self.packets.append((messageType, payload))

    def setService(self, service):
        pass


class UserAuthServerMixin:
    def setUp(self):
        self.portal = Portal(MockRealm())
        self.transport = MockSSHTransport(self.portal)
        self.user_auth = sshserver.SSHUserAuthServer(self.transport)

    def _getMessageName(self, message_type):
        """Get the name of the message for the given message type constant."""
        return userauth.messages[message_type]

    def assertMessageOrder(self, message_types):
        """Assert that the given message types were sent in the order given.
        """
        self.assertEqual(
            [userauth.messages[msg_type] for msg_type in message_types],
            [userauth.messages[packet_type]
             for packet_type, contents in self.transport.packets])

    def assertBannerSent(self, banner_message, expected_language='en'):
        """Assert that 'banner_message' was sent as an SSH banner."""
        # Check that we received a BANNER, then a FAILURE.
        for packet_type, packet_content in self.transport.packets:
            if packet_type == userauth.MSG_USERAUTH_BANNER:
                bytes, language, empty = getNS(packet_content, 2)
                self.assertEqual(banner_message, bytes.decode('UTF8'))
                self.assertEqual(expected_language, language)
                self.assertEqual('', empty)
                break
        else:
            self.fail("No banner logged.")


class TestUserAuthServer(UserAuthServerMixin, unittest.TestCase):

    def test_sendBanner(self):
        # sendBanner should send an SSH 'packet' with type MSG_USERAUTH_BANNER
        # and two fields. The first field is the message itself, and the
        # second is the language tag.
        #
        # sendBanner automatically adds a trailing newline, because openssh
        # and Twisted don't add one when displaying the banner.
        #
        # See RFC 4252, Section 5.4.
        message = u"test message"
        self.user_auth.sendBanner(message, language='en-US')
        self.assertBannerSent(message + '\r\n', 'en-US')
        self.assertEqual(
            1, len(self.transport.packets),
            "More than just banner was sent: %r" % self.transport.packets)

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
        tryAuth = self.user_auth.tryAuth
        self.user_auth.tryAuth = mock_try_auth
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

    Used by TestAuthenticationBannerDisplay to test that errors raised by
    checkers are sent to SSH clients.
    """

    error_message = u'error message'

    def requestAvatarId(self, credentials):
        if credentials.username == 'success':
            return credentials.username
        else:
            return failure.Failure(
                sshserver.UserDisplayedUnauthorizedLogin(self.error_message))


class TestAuthenticationBannerDisplay(UserAuthServerMixin, TrialTestCase):
    """Check that auth error information is passed through to the client.

    Normally, SSH servers provide minimal information on failed authentication.
    With Launchpad, much more user information is public, so it is helpful and
    not insecure to tell users why they failed to authenticate.

    SSH doesn't provide a standard way of doing this, but the
    MSG_USERAUTH_BANNER message is allowed and seems appropriate. See RFC 4252,
    Section 5.4 for more information.
    """

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        UserAuthServerMixin.setUp(self)
        self.portal.registerChecker(MockChecker())
        self.user_auth.serviceStarted()
        self.key_data = self._makeKey()

    def tearDown(self):
        self.user_auth.serviceStopped()

    def _makeKey(self):
        keydir = sibpath(__file__, 'keys')
        public_key = getPublicKeyString(
            data=open(os.path.join(keydir,
                                   'ssh_host_key_rsa.pub'), 'rb').read())
        if isinstance(public_key, str):
            return chr(0) + NS('rsa') + NS(public_key)
        else:
            return chr(0) + NS('rsa') + NS(public_key.blob())

    def requestFailedAuthentication(self):
        return self.user_auth.ssh_USERAUTH_REQUEST(
            NS('failure') + NS('') + NS('publickey') + self.key_data)

    def requestSuccessfulAuthentication(self):
        return self.user_auth.ssh_USERAUTH_REQUEST(
            NS('success') + NS('') + NS('publickey') + self.key_data)

    def requestUnsupportedAuthentication(self):
        # Note that it doesn't matter how the checker responds -- the server
        # doesn't get that far.
        return self.user_auth.ssh_USERAUTH_REQUEST(
            NS('success') + NS('') + NS('none') + NS(''))

    def test_bannerNotSentOnSuccess(self):
        # No banner is printed when the user authenticates successfully.
        self.assertEqual(None, config.codehosting.banner)

        d = self.requestSuccessfulAuthentication()
        def check(ignored):
            # Check that no banner was sent to the user.
            self.assertMessageOrder([userauth.MSG_USERAUTH_SUCCESS])
        return d.addCallback(check)

    def test_configuredBannerSentOnSuccess(self):
        # If a banner is set in the codehosting config then we send it to the
        # user when they log in.
        config.codehosting.banner = "banner"
        d = self.requestSuccessfulAuthentication()
        def check(ignored):
            self.assertMessageOrder(
                [userauth.MSG_USERAUTH_BANNER, userauth.MSG_USERAUTH_SUCCESS])
            self.assertBannerSent(config.codehosting.banner + '\r\n')
        def cleanup(ignored):
            config.codehosting.banner = None
            return ignored
        return d.addCallback(check).addBoth(cleanup)

    def test_configuredBannerSentOnlyOnce(self):
        # We don't send the banner on each authentication attempt, just on the
        # first one. It is usual for there to be many authentication attempts
        # per SSH session.
        config.codehosting.banner = "banner"

        d = self.requestUnsupportedAuthentication()
        d.addCallback(lambda ignored: self.requestSuccessfulAuthentication())

        def check(ignored):
            # Check that no banner was sent to the user.
            self.assertMessageOrder(
                [userauth.MSG_USERAUTH_FAILURE, userauth.MSG_USERAUTH_BANNER,
                 userauth.MSG_USERAUTH_SUCCESS])
            self.assertBannerSent(config.codehosting.banner + '\r\n')

        def cleanup(ignored):
            config.codehosting.banner = None
            return ignored
        return d.addCallback(check).addBoth(cleanup)

    def test_configuredBannerNotSentOnFailure(self):
        # Failed authentication attempts do not get the configured banner
        # sent.
        config.codehosting.banner = 'banner'

        d = self.requestFailedAuthentication()

        def check(ignored):
            self.assertMessageOrder(
                [userauth.MSG_USERAUTH_BANNER, userauth.MSG_USERAUTH_FAILURE])
            self.assertBannerSent(MockChecker.error_message + '\r\n')

        def cleanup(ignored):
            config.codehosting.banner = None
            return ignored

        return d.addCallback(check).addBoth(cleanup)

    def test_loggedToBanner(self):
        # When there's an authentication failure, we display an informative
        # error message through the SSH authentication protocol 'banner'.
        d = self.requestFailedAuthentication()
        def check(ignored):
            # Check that we received a BANNER, then a FAILURE.
            self.assertMessageOrder(
                [userauth.MSG_USERAUTH_BANNER, userauth.MSG_USERAUTH_FAILURE])
            self.assertBannerSent(MockChecker.error_message + '\r\n')
        return d.addCallback(check)

    def test_unsupportedAuthMethodNotLogged(self):
        # Trying various authentication methods is a part of the normal
        # operation of the SSH authentication protocol. We should not spam the
        # client with warnings about this, as whenever it becomes a problem,
        # we can rely on the SSH client itself to report it to the user.
        d = self.requestUnsupportedAuthentication()
        def check(ignored):
            # Check that we received only a FAILRE.
            self.assertMessageOrder([userauth.MSG_USERAUTH_FAILURE])
        return d.addCallback(check)


class TestPublicKeyFromLaunchpadChecker(TrialTestCase):
    """Tests for the SSH server authentication mechanism.

    PublicKeyFromLaunchpadChecker accepts the SSH authentication information
    and contacts the authserver to determine if the given details are valid.

    Any authentication errors are displayed back to the user via an SSH
    MSG_USERAUTH_BANNER message.
    """

    layer = TwistedLaunchpadZopelessLayer

    def setUp(self):
        self.valid_login = 'testuser'
        self.authserver = AuthserverWithKeysInProcess(
            self.valid_login, 'testteam')
        self.authserver.setUp()
        self.authserver_client = TwistedAuthServer(
            config.codehosting.authserver)
        self.checker = sshserver.PublicKeyFromLaunchpadChecker(
            self.authserver_client)
        self.public_key = self.authserver.getPublicKey()
        if not isinstance(self.public_key, str):
            self.public_key = self.public_key.blob()
        self.sigData = (
            NS('') + chr(userauth.MSG_USERAUTH_REQUEST)
            + NS(self.valid_login) + NS('none') + NS('publickey') + '\xff'
            + NS('ssh-dss') + NS(self.public_key))
        Key = getattr(keys, 'Key', None)
        if Key is None:
            self.signature = keys.signData(
                self.authserver.getPrivateKey(), self.sigData)
        else:
            self.signature = self.authserver.getPrivateKey().sign(
                self.sigData)

    def tearDown(self):
        return self.authserver.tearDown()

    def test_successful(self):
        # We should be able to login with the correct public and private
        # key-pair. This test exists primarily as a control to ensure our
        # other tests are checking the right error conditions.
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
            sshserver.UserDisplayedUnauthorizedLogin)
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
        # When you sign into an existing account with no SSH keys, the SSH
        # server should inform you that the account has no keys.
        creds = SSHPrivateKey('lifeless', 'ssh-dss', self.public_key,
                              self.sigData, self.signature)
        return self.assertLoginError(
            creds,
            "Launchpad user %r doesn't have a registered SSH key"
            % 'lifeless')

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
                                   sshserver.UserDisplayedUnauthorizedLogin),
                        "Should not be a UserDisplayedUnauthorizedLogin"))
        return d


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
