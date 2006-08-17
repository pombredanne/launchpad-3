# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['GPGHandler', 'PymeSignature', 'PymeKey', 'PymeUserId']

# standard
import os
import tempfile
import shutil
import urllib
import urllib2
import re
import subprocess
import atexit
from StringIO import StringIO

# launchpad
from canonical.config import config
from canonical.lp.dbschema import GPGKeyAlgorithm

# validators
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.gpg import valid_fingerprint
from canonical.launchpad.validators.gpg import valid_keyid

# zope
from zope.interface import implements
from zope.component import getUtility

# interface
from canonical.launchpad.interfaces import (
    IGPGHandler, IPymeSignature, IPymeKey, IPymeUserId, GPGVerificationError)

# gpgme
import gpgme
import gpgme.editutil


class GPGHandler:
    """See IGPGHandler."""

    implements(IGPGHandler)

    def __init__(self):
        """Initialize environment variable."""
        self._setNewHome()
        os.environ['GNUPGHOME'] = self.home

    def _setNewHome(self):
        """Create a new directory containing the required configuration.

        This method is called inside the class constructor and genereates
        a new directory (name ramdomly generated with the 'gpg-' prefix)
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
        conf.write ('keyserver hkp://%s\n'
                    'keyserver-options auto-key-retrieve\n'
                    'no-auto-check-trustdb\n' % config.gpghandler.host)
        conf.close()
        # create a local atexit handler to remove the configuration directory
        # on normal termination.
        def removeHome(home):
            """Remove GNUPGHOME directory."""
            if os.path.exists(home):
                shutil.rmtree(home)
                
        atexit.register(removeHome, self.home)

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
            # process it
            try:
                signatures = ctx.verify(sig, plain, None)
            except gpgme.GpgmeError, e:
                raise GPGVerificationError(e.message)
        else:
            # store clearsigned signature
            sig = StringIO(content)
            # writeable content
            plain = StringIO()
            # process it
            try:
                signatures = ctx.verify(sig, None, plain)
            except gpgme.GpgmeError, e:
                raise GPGVerificationError(e.message)

        # XXX 20060131 jamesh
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
            raise GPGVerificationError(signature.status.message)

        # supporting subkeys by retriving the full key from the
        # keyserver and use the master key fingerprint.
        result, key = self.retrieveKey(signature.fpr)
        if not result:
            raise GPGVerificationError("Unable to map subkey: %s" % key)
        
        # return the signature container
        return PymeSignature(fingerprint=key.fingerprint,
                             plain_data=plain.getvalue())

    def importKey(self, content):
        """See IGPGHandler."""        
        ctx = gpgme.Context()
        ctx.armor = True

        newkey = StringIO(content)
        result = ctx.import_(newkey)

        # Multiple keys supplied which one was desired is unknown
        if len(result.imports) != 1:
            return None

        fingerprint, res, status = result.imports[0]
        # if it's a secret key, simply returns
        if status & gpgme.IMPORT_SECRET != 0:
            return None

        key = PymeKey(fingerprint)

        # pubkey not recognized
        if key.fingerprint is None:
            return None

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

    def decryptContent(self, content, password):
        """See IGPGHandler."""

        if isinstance(password, unicode):
            raise TypeError('Password cannot be Unicode.')

        if isinstance(content, unicode):
            raise TypeError('Content cannot be Unicode.')

        # setup context
        ctx = gpgme.Context()
        ctx.armor = True

        # setup containers
        cipher = StringIO(content)
        plain = StringIO()

        def passphrase_cb(uid_hint, passphrase_info, prev_was_bad, fd):
            os.write(fd, '%s\n' % password)

        ctx.passphrase_cb = passphrase_cb

        # Do the deecryption.
        try:
            ctx.decrypt(cipher, plain)
        except gpgme.GpgmeError:
            return None

        return plain.getvalue()

    def localKeys(self):
        """Get an iterator of the keys this gpg handler
        already knows about.
        """
        ctx = gpgme.Context()
        for key in ctx.keylist():
            yield PymeKey.newFromGpgmeKey(key)

    def retrieveKey(self, fingerprint):
        """See IGPGHandler."""
        # XXX cprov 20050705
        # Integrate it with the furure proposal related 
        # synchronization of the local key ring with the 
        # global one. It should basically consists of be
        # aware of a revoked flag coming from the global
        # key ring, but it needs "specing" 
        
        # verify if key is present in the local key ring
        key = PymeKey(fingerprint.encode('ascii'))
        # if not try to import from key server
        if not key.fingerprint:
            result, pubkey = self._getPubKey(fingerprint)
            # if not found return 
            if not result:
                return False, pubkey 
            # try to import in the local key ring
            key = self.importKey(pubkey)
            if not key:
                return False, '<Could not import to local key ring>'

        return True, key

    def getURLForKeyInServer(self, fingerprint, action='index'):
        """See IGPGHandler"""
        params = {
            'search': '0x%s' % fingerprint[-8:],
            'op': action
        }
        return 'http://%s:%s/pks/lookup?%s' % (config.gpghandler.host,
                                               config.gpghandler.port,
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
        # XXX cprov 20050516
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


class PymeSignature(object):
    """See IPymeSignature."""
    implements(IPymeSignature)

    def __init__(self, fingerprint=None, plain_data=None):
        """Initialized a signature container."""
        self.fingerprint = fingerprint
        self.plain_data = plain_data


class PymeKey:
    """See IPymeKey."""
    implements(IPymeKey)

    def __init__(self, fingerprint):
        """Inititalize a key container."""
        self.fingerprint = None
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
        # create a new particular context
        ctx = gpgme.Context()
        # retrive additional key information
        try:
            key = ctx.get_key(fingerprint, False)
        except gpgme.GpgmeError:
            key = None

        if key and valid_fingerprint(key.subkeys[0].fpr):
            self._buildFromGpgmeKey(key)

    def _buildFromGpgmeKey(self, key):
        self.fingerprint = key.subkeys[0].fpr
        self.keyid = self.fingerprint[-8:]
        self.algorithm = GPGKeyAlgorithm.items[key.subkeys[0].pubkey_algo].title
        self.revoked = key.subkeys[0].revoked
        self.expired = key.expired
        self.keysize = key.subkeys[0].length
        self.owner_trust = key.owner_trust
        self.can_encrypt = key.can_encrypt
        self.can_sign = key.can_sign
        self.can_certify = key.can_certify
        self.can_authenticate = key.can_authenticate

        # copy the UIDs 
        self.uids = []
        for uid in key.uids:
            self.uids.append(PymeUserId(uid))

        # the non-revoked valid email addresses associated with this key
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
        gpgme.editutil.edit_trust(ctx, key, value)
        # set the cached copy of owner_trust
        self.owner_trust = value
    
    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm, self.keyid)


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
