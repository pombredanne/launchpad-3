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

# pyme
import pyme.core
import pyme.errors
from pyme.constants import validity

# XXX: 20051006 jamesh
# this constant should also be exported in the pyme.constants.import module,
# but said module can not be imported, due to it's name being a keyword ...
from pyme._gpgme import GPGME_IMPORT_SECRET

from pyme.gpgme import gpgme_strerror


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

        c = pyme.core.Context()

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
            sig = pyme.core.Data(signature)
            # store the content
            plain = pyme.core.Data(content)
            # process it
            try:
                c.op_verify(sig, plain, None)
            except pyme.errors.GPGMEError, e:
                raise GPGVerificationError(str(e))
        else:
            # store clearsigned signature
            sig = pyme.core.Data(content)
            # writeable content
            plain = pyme.core.Data()
            # process it
            try:
                c.op_verify(sig, None, plain)
            except pyme.errors.GPGMEError, e:
                raise GPGVerificationError(str(e))
        
        result = c.op_verify_result()

        # XXX 20060131 jamesh
        # We raise an exception if we don't get exactly one signature.
        # If we are verifying a clear signed document, multiple signatures
        # may indicate two differently signed sections concatenated
        # together.
        # Multiple signatures for the same signed block of data is possible,
        # but uncommon.  If people complain, we'll need to examine the issue
        # again.
        
        # if no signatures were found, raise an error:
        if result.signatures is None:
            raise GPGVerificationError('No signatures found')
        # we only expect a single signature:
        if result.signatures.next is not None:
            raise GPGVerificationError('Single signature expected, '
                                       'found multiple signatures')

        signature = result.signatures

        # signature.status == 0 means "Ok"
        if signature.status != 0:
            raise GPGVerificationError(gpgme_strerror(signature.status))

        # supporting subkeys by retriving the full key from the
        # keyserver and use the master key fingerprint.
        result, key = self.retrieveKey(signature.fpr)
        if not result:
            raise GPGVerificationError("Unable to map subkey: %s" % key)
        
        plain.seek(0, 0)
        plain_data = plain.read()


        # return the signature container
        return PymeSignature(fingerprint=key.fingerprint,
                             plain_data=plain_data)

    def importKey(self, content):
        """See IGPGHandler."""        
        c = pyme.core.Context()
        c.set_armor(1)

        newkey = pyme.core.Data(content)
        c.op_import(newkey)
        result = c.op_import_result()

        # Multiple keys supplied which one was desired is unknown
        if result.imports is None or result.imports.next is not None:
            return None

        # if it's a secret key, simply returns
        if result.imports.status & GPGME_IMPORT_SECRET != 0:
            return None
        
        fingerprint = result.imports.fpr

        key = PymeKey(fingerprint)

        # pubkey not recognized
        if key.fingerprint is None:
            return None

        return key

    def importKeyringFile(self, filepath):
        """See IGPGHandler.importKeyringFile."""
        context = pyme.core.Context()
        data = pyme.core.Data()
        data.new_from_file(filepath)
        context.op_import(data)
        result = context.op_import_result()
        # if not considered -> format wasn't recognized
        # no key was imported
        if result.considered == 0:
            raise ValueError('Empty or invalid keyring')
        imported = result.imports
        result = []
        while imported is not None:
            result.append(PymeKey(imported.fpr))
            imported = imported.next
        return result

    def encryptContent(self, content, fingerprint):
        """See IGPGHandler."""
        if isinstance(content, unicode):
            raise TypeError('Content cannot be Unicode.')

        # setup context
        c = pyme.core.Context()
        c.set_armor(1)

        # setup containers
        plain = pyme.core.Data(content)
        cipher = pyme.core.Data()

        # retrive pyme key object
        try:
            key = c.get_key(fingerprint.encode('ascii'), 0)
        except pyme.errors.GPGMEError:
            return None

        if not key.can_encrypt:
            raise ValueError('key %s can not be used for encryption'
                             % fingerprint)

        # encrypt content
        c.op_encrypt([key], 1, plain, cipher)
        cipher.seek(0,0)

        return cipher.read()

    def decryptContent(self, content, password):
        """See IGPGHandler."""

        if isinstance(password, unicode):
            raise TypeError('Password cannot be Unicode.')

        if isinstance(content, unicode):
            raise TypeError('Content cannot be Unicode.')

        # setup context
        c = pyme.core.Context()
        c.set_armor(1)

        # setup containers
        cipher = pyme.core.Data(content)
        plain = pyme.core.Data()

        # Do the deecryption.
        c.set_passphrase_cb(lambda x,y,z: password, None)
        try:
            c.op_decrypt(cipher, plain)
        except pyme.errors.GPGMEError:
            return None

        plain.seek(0,0)

        return plain.read()

    def localKeys(self):
        """Get an iterator of the keys this gpg handler
        already knows about.
        """
        context = pyme.core.Context()
        for key in context.op_keylist_all():
            # subkeys is the first in a C object based list
            # use .next to find the next subkey
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
        keyid = fingerprint[-8:]

        params = urllib.urlencode({'op': action,
                                   'search': '0x%s' % keyid})

        url = 'http://%s:%s/pks/lookup?%s' % (config.gpghandler.host,
                                              config.gpghandler.port,
                                              params)
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
        c = pyme.core.Context()
        # retrive additional key information
        try:
            key = c.get_key(fingerprint, 0)
        except pyme.errors.GPGMEError:
            key = None

        if key and valid_fingerprint(key.subkeys.fpr):
            self._buildFromGpgmeKey(key)

    def _buildFromGpgmeKey(self, key):
        self.fingerprint = key.subkeys.fpr
        self.keyid = key.subkeys.fpr[-8:]
        self.algorithm = GPGKeyAlgorithm.items[key.subkeys.pubkey_algo].title
        self.revoked = bool(key.subkeys.revoked)
        self.expired = bool(key.expired)
        self.keysize = key.subkeys.length
        self.owner_trust = key.owner_trust
        self.can_encrypt = bool(key.can_encrypt)
        self.can_sign = bool(key.can_sign)
        self.can_certify = bool(key.can_certify)
        self.can_authenticate = bool(key.can_authenticate)

        # copy the UIDs 
        self.uids = []
        uid = key.uids
        while uid is not None:
            self.uids.append(PymeUserId(uid))
            uid = uid.next

        # the non-revoked valid email addresses associated with this key
        self.emails = [uid.email for uid in self.uids
                       if valid_email(uid.email) and not uid.revoked]

    def setOwnerTrust(self, value): 
        """Set the ownertrust on the actual gpg key"""
        if value not in (validity.UNDEFINED, validity.NEVER,
                         validity.MARGINAL, validity.FULL,
                         validity.ULTIMATE):
            raise ValueError("invalid owner trust level")
        # edit the owner trust value on the key
        context = pyme.core.Context()
        key = context.get_key(self.fingerprint.encode('ascii'), False)
        context.op_edit_trust(key, value)
        # set the cached copy of owner_trust
        self.owner_trust = value
    
    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm, self.keyid)


class PymeUserId:
    """See IPymeUserId"""
    implements(IPymeUserId)

    def __init__(self, uid):
        self.revoked = bool(uid.revoked)
        self.invalid = bool(uid.invalid)
        self.validity = uid.validity
        self.uid = uid.uid
        self.name = uid.name
        self.email = uid.email
        self.comment = uid.comment
