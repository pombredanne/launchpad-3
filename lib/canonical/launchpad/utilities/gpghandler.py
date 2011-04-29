# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'GPGHandler',
    'LongRunningGPGHandler',
    'PymeKey',
    'PymeSignature',
    'PymeUserId',
    ]

import atexit
import httplib
import os
import re
import shutil
import socket
from StringIO import StringIO
import subprocess
import tempfile
import urllib
import urllib2

import gpgme
from gpgme import editutil as gpgme_editutil
from twisted.internet import task
from twisted.internet.error import AlreadyCancelled
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.gpghandler import (
    GPGKeyExpired,
    GPGKeyNotFoundError,
    GPGKeyRevoked,
    GPGUploadFailure,
    GPGVerificationError,
    IGPGHandler,
    IPymeKey,
    IPymeSignature,
    IPymeUserId,
    MoreThanOneGPGKeyFound,
    SecretGPGKeyImportDetected,
    )
from lp.app.validators.email import valid_email
from lp.registry.interfaces.gpg import (
    GPGKeyAlgorithm,
    valid_fingerprint,
    )


signing_only_param = """
<GnupgKeyParms format="internal">
  Key-Type: RSA
  Key-Usage: sign
  Key-Length: 1024
  Name-Real: %(name)s
  Expire-Date: 0
</GnupgKeyParms>
"""


class GPGHandler:
    """See IGPGHandler."""

    implements(IGPGHandler)

    def __init__(self):
        """Initialize environment variable."""
        self._startup()
        os.environ['GNUPGHOME'] = self.home

    def _startup(self):
        """Create a new directory containing the required configuration.

        This method is called inside the class constructor and genereates
        a new directory (name randomly generated with the 'gpg-' prefix)
        containing the proper file configuration and options.

        Also installs an atexit handler to remove the directory on normal
        process termination.
        """
        self.home = tempfile.mkdtemp(prefix='gpg-')
        confpath = os.path.join(self.home, 'gpg.conf')
        conf = open(confpath, 'w')
        # set needed GPG options, 'auto-key-retrieve' is necessary for
        # automatically retrieve from the keyserver unknown key when
        # verifying signatures and 'no-auto-check-trustdb' avoid wasting
        # time verifying the local keyring consistence.
        conf.write('keyserver hkp://%s\n'
                   'keyserver-options auto-key-retrieve\n'
                   'no-auto-check-trustdb\n' % config.gpghandler.host)
        conf.close()
        # register an atexit handler to remove the configuration directory
        # on normal termination.
        atexit.register(self._shutdown)

    def _shutdown(self):
        """Remove GNUPGHOME directory."""
        if os.path.exists(self.home):
            shutil.rmtree(self.home)

    def sanitizeFingerprint(self, fingerprint):
        """See IGPGHandler."""
        # remove whitespaces, truncate to max of 40 (as per v4 keys) and
        # convert to upper case
        fingerprint = fingerprint.replace(' ', '')
        fingerprint = fingerprint[:40].upper()

        if not valid_fingerprint(fingerprint):
            return None

        return fingerprint

    def resetLocalState(self):
        """See IGPGHandler."""
        # remove the public keyring, private keyring and the trust DB
        for filename in ['pubring.gpg', 'secring.gpg', 'trustdb.gpg']:
            filename = os.path.join(self.home, filename)
            if os.path.exists(filename):
                os.remove(filename)

    def verifySignature(self, content, signature=None):
        """See IGPGHandler."""
        try:
            return self.getVerifiedSignature(content, signature)
        except GPGVerificationError:
            # Swallow GPG Verification Errors
            pass
        return None

    def getVerifiedSignatureResilient(self, content, signature=None):
        """See IGPGHandler."""
        errors = []

        for i in range(3):
            try:
                signature = self.getVerifiedSignature(content, signature)
            except GPGVerificationError, info:
                errors.append(info)
            else:
                return signature

        stored_errors = [str(err) for err in errors]

        raise GPGVerificationError(
            "Verification failed 3 times: %s " % stored_errors)

    def getVerifiedSignature(self, content, signature=None):
        """See IGPGHandler."""

        assert not isinstance(content, unicode)
        assert not isinstance(signature, unicode)

        ctx = gpgme.Context()

        # from `info gpgme` about gpgme_op_verify(SIG, SIGNED_TEXT, PLAIN):
        #
        # If SIG is a detached signature, then the signed text should be
        # provided in SIGNED_TEXT and PLAIN should be a null pointer.
        # Otherwise, if SIG is a normal (or cleartext) signature,
        # SIGNED_TEXT should be a null pointer and PLAIN should be a
        # writable data object that will contain the plaintext after
        # successful verification.

        if signature:
            # store detach-sig
            sig = StringIO(signature)
            # store the content
            plain = StringIO(content)
            args = (sig, plain, None)
        else:
            # store clearsigned signature
            sig = StringIO(content)
            # writeable content
            plain = StringIO()
            args = (sig, None, plain)

        # process it
        try:
            signatures = ctx.verify(*args)
        except gpgme.GpgmeError, e:
            # XXX: 2010-04-26, Salgado, bug=570244: This hack is needed
            # for python2.5 compatibility. We should remove it when we no
            # longer need to run on python2.5.
            if hasattr(e, 'strerror'):
                msg = e.strerror
            else:
                msg = e.message
            raise GPGVerificationError(msg)

        # XXX jamesh 2006-01-31:
        # We raise an exception if we don't get exactly one signature.
        # If we are verifying a clear signed document, multiple signatures
        # may indicate two differently signed sections concatenated
        # together.
        # Multiple signatures for the same signed block of data is possible,
        # but uncommon.  If people complain, we'll need to examine the issue
        # again.

        # if no signatures were found, raise an error:
        if len(signatures) == 0:
            raise GPGVerificationError('No signatures found')
        # we only expect a single signature:
        if len(signatures) > 1:
            raise GPGVerificationError('Single signature expected, '
                                       'found multiple signatures')

        signature = signatures[0]
        # signature.status == 0 means "Ok"
        if signature.status is not None:
            raise GPGVerificationError(signature.status.args)

        # supporting subkeys by retriving the full key from the
        # keyserver and use the master key fingerprint.
        try:
            key = self.retrieveKey(signature.fpr)
        except GPGKeyNotFoundError:
            raise GPGVerificationError(
                "Unable to map subkey: %s" % signature.fpr)

        # return the signature container
        return PymeSignature(
            fingerprint=key.fingerprint,
            plain_data=plain.getvalue(),
            timestamp=signature.timestamp)

    def importPublicKey(self, content):
        """See IGPGHandler."""
        assert isinstance(content, str)
        context = gpgme.Context()
        context.armor = True

        newkey = StringIO(content)
        result = context.import_(newkey)

        if len(result.imports) == 0:
            raise GPGKeyNotFoundError(content)

        # Check the status of all imported keys to see if any of them is
        # a secret key.  We can't rely on result.secret_imported here
        # because if there's a secret key which is already imported,
        # result.secret_imported will be 0.
        for fingerprint, res, status in result.imports:
            if status & gpgme.IMPORT_SECRET != 0:
                raise SecretGPGKeyImportDetected(
                    "GPG key '%s' is a secret key." % fingerprint)

        if len(result.imports) > 1:
            raise MoreThanOneGPGKeyFound('Found %d GPG keys when importing %s'
                                         % (len(result.imports), content))

        fingerprint, res, status = result.imports[0]
        key = PymeKey(fingerprint)
        assert key.exists_in_local_keyring
        return key

    def importSecretKey(self, content):
        """See `IGPGHandler`."""
        assert isinstance(content, str)

        # Make sure that gpg-agent doesn't interfere.
        if 'GPG_AGENT_INFO' in os.environ:
            del os.environ['GPG_AGENT_INFO']

        context = gpgme.Context()
        context.armor = True
        newkey = StringIO(content)
        import_result = context.import_(newkey)

        secret_imports = [
            fingerprint
            for fingerprint, result, status in import_result.imports
            if status & gpgme.IMPORT_SECRET]
        if len(secret_imports) != 1:
            raise MoreThanOneGPGKeyFound(
                'Found %d secret GPG keys when importing %s'
                % (len(secret_imports), content))

        fingerprint, result, status = import_result.imports[0]
        try:
            key = context.get_key(fingerprint, True)
        except gpgme.GpgmeError:
            return None

        key = PymeKey.newFromGpgmeKey(key)
        assert key.exists_in_local_keyring
        return key

    def generateKey(self, name):
        """See `IGPGHandler`."""
        context = gpgme.Context()

        # Make sure that gpg-agent doesn't interfere.
        if 'GPG_AGENT_INFO' in os.environ:
            del os.environ['GPG_AGENT_INFO']

        # Only 'utf-8' encoding is supported by gpgme.
        # See more information at:
        # http://pyme.sourceforge.net/doc/gpgme/Generating-Keys.html
        result = context.genkey(
            signing_only_param % {'name': name.encode('utf-8')})

        # Right, it might seem paranoid to have this many assertions,
        # but we have to take key generation very seriously.
        assert result.primary, 'Secret key generation failed.'
        assert not result.sub, (
            'Only sign-only RSA keys are safe to be generated')

        secret_keys = list(self.localKeys(result.fpr, secret=True))

        assert len(secret_keys) == 1, 'Found %d secret GPG keys for %s' % (
            len(secret_keys), result.fpr)

        key = secret_keys[0]

        assert key.fingerprint == result.fpr, (
            'The key in the local keyring does not match the one generated.')
        assert key.exists_in_local_keyring, (
            'The key does not seem to exist in the local keyring.')

        return key

    def importKeyringFile(self, filepath):
        """See IGPGHandler.importKeyringFile."""
        ctx = gpgme.Context()
        data = open(filepath, 'r')
        result = ctx.import_(data)
        # if not considered -> format wasn't recognized
        # no key was imported
        if result.considered == 0:
            raise ValueError('Empty or invalid keyring')
        return [PymeKey(fingerprint)
                for (fingerprint, result, status) in result.imports]

    def encryptContent(self, content, fingerprint):
        """See IGPGHandler."""
        if isinstance(content, unicode):
            raise TypeError('Content cannot be Unicode.')

        # setup context
        ctx = gpgme.Context()
        ctx.armor = True

        # setup containers
        plain = StringIO(content)
        cipher = StringIO()

        # retrive gpgme key object
        try:
            key = ctx.get_key(fingerprint.encode('ascii'), 0)
        except gpgme.GpgmeError:
            return None

        if not key.can_encrypt:
            raise ValueError('key %s can not be used for encryption'
                             % fingerprint)

        # encrypt content
        ctx.encrypt([key], gpgme.ENCRYPT_ALWAYS_TRUST, plain, cipher)

        return cipher.getvalue()

    def signContent(self, content, key_fingerprint, password='', mode=None):
        """See IGPGHandler."""
        if not isinstance(content, str):
            raise TypeError('Content should be a string.')

        if mode is None:
            mode = gpgme.SIG_MODE_CLEAR

        # Find the key and make it the only one allowed to sign content
        # during this session.
        context = gpgme.Context()
        context.armor = True

        key = context.get_key(key_fingerprint.encode('ascii'), True)
        context.signers = [key]

        # Set up containers.
        plaintext = StringIO(content)
        signature = StringIO()

        # Make sure that gpg-agent doesn't interfere.
        if 'GPG_AGENT_INFO' in os.environ:
            del os.environ['GPG_AGENT_INFO']

        def passphrase_cb(uid_hint, passphrase_info, prev_was_bad, fd):
            os.write(fd, '%s\n' % password)
        context.passphrase_cb = passphrase_cb

        # Sign the text.
        try:
            context.sign(plaintext, signature, mode)
        except gpgme.GpgmeError:
            return None

        return signature.getvalue()

    def localKeys(self, filter=None, secret=False):
        """Get an iterator of the keys this gpg handler
        already knows about.
        """
        ctx = gpgme.Context()

        # XXX michaeln 2010-05-07 bug=576405
        # Currently gpgme.Context().keylist fails if passed a unicode
        # string even though that's what is returned for fingerprints.
        if type(filter) == unicode:
            filter = filter.encode('utf-8')

        for key in ctx.keylist(filter, secret):
            yield PymeKey.newFromGpgmeKey(key)

    def retrieveKey(self, fingerprint):
        """See IGPGHandler."""
        # XXX cprov 2005-07-05:
        # Integrate it with the furure proposal related
        # synchronization of the local key ring with the
        # global one. It should basically consists of be
        # aware of a revoked flag coming from the global
        # key ring, but it needs "specing"
        key = PymeKey(fingerprint.encode('ascii'))
        if not key.exists_in_local_keyring:
            result, pubkey = self._getPubKey(fingerprint)
            if not result:
                if "Connection refused" in pubkey:
                    raise AssertionError(
                        "The keyserver is not running, help!")
                else:
                    raise GPGKeyNotFoundError(fingerprint, pubkey)

            # Import in the local key ring
            key = self.importPublicKey(pubkey)
        return key

    def retrieveActiveKey(self, fingerprint):
        """See `IGPGHandler`."""
        key = self.retrieveKey(fingerprint)
        if key.revoked:
            raise GPGKeyRevoked(key)
        if key.expired:
            raise GPGKeyExpired(key)
        return key

    def _submitKey(self, content):
        """Submit an ASCII-armored public key export to the keyserver.

        It issues a POST at /pks/add on the keyserver specified in the
        configuration.
        """
        keyserver_http_url = '%s:%s' % (
            config.gpghandler.host, config.gpghandler.port)

        conn = httplib.HTTPConnection(keyserver_http_url)
        params = urllib.urlencode({'keytext': content})
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/plain",
            }

        try:
            conn.request("POST", "/pks/add", params, headers)
        except socket.error, err:
            raise GPGUploadFailure(
                'Could not reach keyserver at http://%s %s' % (
                    keyserver_http_url, str(err)))

        assert conn.getresponse().status == httplib.OK, (
            'Keyserver POST failed')

        conn.close()

    def uploadPublicKey(self, fingerprint):
        """See IGPGHandler"""
        pub_key = self.retrieveKey(fingerprint)
        self._submitKey(pub_key.export())

    def getURLForKeyInServer(self, fingerprint, action='index', public=False):
        """See IGPGHandler"""
        params = {
            'search': '0x%s' % fingerprint,
            'op': action,
            }
        if public:
            host = config.gpghandler.public_host
        else:
            host = config.gpghandler.host
        return 'http://%s:%s/pks/lookup?%s' % (host, config.gpghandler.port,
                                               urllib.urlencode(params))

    def _getKeyIndex(self, fingerprint):
        """See IGPGHandler for further information."""
        # Grab Page from keyserver
        result, page = self._grabPage('index', fingerprint)

        if not result:
            return result, page

        # regexps to extract information
        htmltag_re = re.compile('<[^>]+>')
        keyinfo_re = re.compile('([\d]*)([RgDG])\/([\dABCDEF]*)')
        emailaddresses_re = re.compile('[^;]+@[^&]*')

        # clean html tags from page
        page = htmltag_re.sub('', page)

        # extract key info as [(size, type, id)]
        keyinfo = keyinfo_re.findall(page)
        # extract UIDs as sorted list
        uids = emailaddresses_re.findall(page)

        # sort the UID list
        uids.sort()

        return keyinfo, uids

    def _getPubKey(self, fingerprint):
        """See IGPGHandler for further information."""
        return self._grabPage('get', fingerprint)

    def _grabPage(self, action, fingerprint):
        """Wrapper to collect KeyServer Pages."""
        # XXX cprov 2005-05-16:
        # What if something went wrong ?
        # 1 - Not Found
        # 2 - Revoked Key
        # 3 - Server Error (solved with urllib2.HTTPError exception)
        # it needs more love
        url = self.getURLForKeyInServer(fingerprint, action)
        # read and store html page
        try:
            f = urllib2.urlopen(url)
        except urllib2.URLError, e:
            return False, '%s at %s' % (e, url)

        page = f.read()
        f.close()

        return True, page

    def checkTrustDb(self):
        """See IGPGHandler"""
        p = subprocess.Popen(['gpg', '--check-trustdb', '--batch', '--yes'],
                             close_fds=True,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        p.communicate()
        return p.returncode


class LongRunningGPGHandler(GPGHandler):
    """See `IGPGHandler`.

    This implementation starts a twisted job to periodically touch all the
    files in the config directory under /tmp, to prevent them from being
    cleaned up.
    """

    implements(IGPGHandler)

    def _startup(self):
        """Set up the twisted job to periodically touch the config directory.
        """
        super(LongRunningGPGHandler, self)._startup()
        self._touch_home_call = None
        self._scheduleTouchHomeDirectoryJob()

    def _shutdown(self):
        """Stop the twisted job as part of shutting down."""
        try:
            self.stopConfigJob()
        except AlreadyCancelled:
            # So we're already cancelled, meh.
            pass
        super(LongRunningGPGHandler, self)._shutdown()

    def stopConfigJob(self):
        """Required for tests.

        Tests which extend _DeferredRunTest complain if there are any
        pending jobs when they complete. So we need a way to allow them to
        manually stop the config job rather than waiting for the atexit
        callback to do it.
        """
        if self._touch_home_call and self._touch_home_call.running:
            self._touch_home_call.stop()

    def _touchFilesInHomeDirectory(self):
        os.utime(self.home, None)
        for file in os.listdir(self.home):
            try:
                os.utime(os.path.join(self.home, file), None)
            except OSError:
                # The file has been deleted.
                pass

    def _scheduleTouchHomeDirectoryJob(self, touch_interval=12*3600):
        # Create a job to touch the home directory every 12 hours so that it
        # does not get cleaned up by any reaper scripts which look at
        # time last modified. This is done outside of _setHome to allow a
        # test to be written which sets the touch interval to a value short
        # enough for a viable test.

        self.stopConfigJob()
        self._touch_home_call = task.LoopingCall(
            self._touchFilesInHomeDirectory)
        return self._touch_home_call.start(touch_interval)


class PymeSignature(object):
    """See IPymeSignature."""
    implements(IPymeSignature)

    def __init__(self, fingerprint=None, plain_data=None, timestamp=None):
        """Initialized a signature container."""
        self.fingerprint = fingerprint
        self.plain_data = plain_data
        self.timestamp = timestamp


class PymeKey:
    """See IPymeKey."""
    implements(IPymeKey)

    fingerprint = None
    exists_in_local_keyring = False

    def __init__(self, fingerprint):
        """Inititalize a key container."""
        if fingerprint:
            self._buildFromFingerprint(fingerprint)

    @classmethod
    def newFromGpgmeKey(cls, key):
        """Initialize a PymeKey from a gpgme_key_t instance."""
        self = cls(None)
        self._buildFromGpgmeKey(key)
        return self

    def _buildFromFingerprint(self, fingerprint):
        """Build key information from a fingerprint."""
        context = gpgme.Context()
        # retrive additional key information
        try:
            key = context.get_key(fingerprint, False)
        except gpgme.GpgmeError:
            key = None

        if key and valid_fingerprint(key.subkeys[0].fpr):
            self._buildFromGpgmeKey(key)

    def _buildFromGpgmeKey(self, key):
        self.exists_in_local_keyring = True
        subkey = key.subkeys[0]
        self.fingerprint = subkey.fpr
        self.revoked = subkey.revoked
        self.keysize = subkey.length

        self.algorithm = GPGKeyAlgorithm.items[subkey.pubkey_algo].title
        self.keyid = self.fingerprint[-8:]
        self.expired = key.expired
        self.secret = key.secret
        self.owner_trust = key.owner_trust
        self.can_encrypt = key.can_encrypt
        self.can_sign = key.can_sign
        self.can_certify = key.can_certify
        self.can_authenticate = key.can_authenticate

        self.uids = [PymeUserId(uid) for uid in key.uids]

        # Non-revoked valid email addresses associated with this key
        self.emails = [uid.email for uid in self.uids
                       if valid_email(uid.email) and not uid.revoked]

    def setOwnerTrust(self, value):
        """Set the ownertrust on the actual gpg key"""
        if value not in (gpgme.VALIDITY_UNDEFINED, gpgme.VALIDITY_NEVER,
                         gpgme.VALIDITY_MARGINAL, gpgme.VALIDITY_FULL,
                         gpgme.VALIDITY_ULTIMATE):
            raise ValueError("invalid owner trust level")
        # edit the owner trust value on the key
        ctx = gpgme.Context()
        key = ctx.get_key(self.fingerprint.encode('ascii'), False)
        gpgme_editutil.edit_trust(ctx, key, value)
        # set the cached copy of owner_trust
        self.owner_trust = value

    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm, self.keyid)

    def export(self):
        """See `PymeKey`."""
        if self.secret:
            # XXX cprov 20081014: gpgme_op_export() only supports public keys.
            # See http://www.fifi.org/cgi-bin/info2www?(gpgme)Exporting+Keys
            p = subprocess.Popen(
                ['gpg', '--export-secret-keys', '-a', self.fingerprint],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            return p.stdout.read()

        context = gpgme.Context()
        context.armor = True
        keydata = StringIO()
        context.export(self.fingerprint.encode('ascii'), keydata)

        return keydata.getvalue()


class PymeUserId:
    """See IPymeUserId"""
    implements(IPymeUserId)

    def __init__(self, uid):
        self.revoked = uid.revoked
        self.invalid = uid.invalid
        self.validity = uid.validity
        self.uid = uid.uid
        self.name = uid.name
        self.email = uid.email
        self.comment = uid.comment
