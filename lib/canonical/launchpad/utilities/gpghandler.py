# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['GPGHandler', 'PymeSignature', 'PymeKey']

# standard
import os
import shutil
import urllib
import urllib2
import re

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
    IGPGHandler, IPymeSignature, IPymeKey)

# pyme
import pyme.core
import pyme.errors
from pyme.constants import validity


class GPGHandler:
    """See IGPGHandler."""

    implements(IGPGHandler)

    def __init__(self):
        """Initialize environment variable."""
        self.home = config.gpghandler.home
        self.reset_local_state()
        os.environ['GNUPGHOME'] = self.home

    # XXX cprov 20050516
    # Is not thread safe ... should it be ?
    def reset_local_state(self):
        """Recreate the directory and the configuration file."""
        #FIXME RBC: this should be a zope test cleanup thing per SteveA.
        #while still allowing __init__ to use it.
        # remove if it already exists
        if os.access(self.home, os.F_OK):
            shutil.rmtree(self.home)

        os.mkdir(self.home)
        confpath = os.path.join(self.home, 'gpg.conf')
        conf = open(confpath, 'w')
        conf.write ('keyserver hkp://%s\n'
                    'keyserver-options auto-key-retrieve\n'
                    'no-auto-check-trustdb\n' % config.gpghandler.host)
        conf.close()

    # XXX cprov 20050414
    # Instantiate a pyme.core.Context() per method, in that way
    # we can perform action in parallel (thread safe)
    def verifySignature(self, content, signature=None):
        """See IGPGHandler."""

        if isinstance(content, unicode):
            raise TypeError('Content cannot be Unicode.')

        if isinstance(signature, unicode):
            raise TypeError('Content cannot be Unicode.')

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
            except pyme.errors.GPGMEError:
                return None
        else:
            # store clearsigned signature
            sig = pyme.core.Data(content)
            # writeable content
            plain = pyme.core.Data()
            # process it
            try:
                c.op_verify(sig, None, plain)
            except pyme.errors.GPGMEError:
                return None
        
        result = c.op_verify_result()

        # XXX cprov 20050328
        # it doesn't support multiple signatures yet
        signature = result.signatures

        # signature.status == 0 means "Ok"
        if signature.status != 0:
            return None

        # supporting subkeys by retriving the full key from the
        # keyserver and use the master key fingerprint.
        result, key = self.retrieveKey(signature.fpr)
        if not result:
            return None
        
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

        # if not considered -> format wasn't recognized
        # no key was imported
        if result.considered == 0:
            return None

        # if it's a secret key, simply returns
        if result.secret_imported == 1:
            return None

        fingerprint = result.imports.fpr

        if result.imported != 1:
            # Multiple keys supplied which one was desired is unknown
            return None

        key = PymeKey(fingerprint)

        # pubkey not recognized
        if key == None:
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
            key = c.get_key(fingerprint.encde('ascii'), 0)
        except pyme.errors.GPGMEError:
            return None
        
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

    def local_keys(self):
        """Get an iterator of the keys this gpg handler
        already knows about.
        """
        context = pyme.core.Context()
        for key in context.op_keylist_all():
            # subkeys is the first in a C object based list
            # use .next to find the next subkey
            yield PymeKey(key.subkeys.fpr)

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
        if not fingerprint:
            return
        self._buildKey(fingerprint)

    def _buildKey(self, fingerprint):
        # create a new particular context
        c = pyme.core.Context()
        # retrive additional key information
        try:
            key = c.get_key(fingerprint, 0)
        except pyme.errors.GPGMEError:
            key = None

        if not (key and valid_fingerprint(key.subkeys.fpr)):
            self.fingerprint = None
            return

        self.fingerprint = key.subkeys.fpr
        self.keyid = key.subkeys.fpr[-8:]
        self.algorithm = GPGKeyAlgorithm.items[key.subkeys.pubkey_algo].title
        self.revoked = key.subkeys.revoked
        self.keysize = key.subkeys.length
        self._owner_trust = key.owner_trust

        # copy the UIDs 
        self.uids = []
        uid = key.uids
        while uid:
            # we expect only one emailaddress by UID
            if valid_email(uid.email) and not uid.revoked:
                self.uids.append(uid.email)
            uid = uid.next
        
    def _gpg_key(self, fingerprint=None):
        """Get the underlying gpg key."""
        if fingerprint is None:
            fingerprint = self.fingerprint
        context = pyme.core.Context()
        return context.get_key(fingerprint.encode('ascii'), 0)

    def owner_trust(self):
        """The owner trust value for the key"""
        return self._owner_trust
        
    def set_owner_trust(self, value): 
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
        self._owner_trust = value
    
    owner_trust = property(owner_trust, set_owner_trust)
    del set_owner_trust

    @property
    def displayname(self):
        return '%s%s/%s' % (self.keysize, self.algorithm, self.keyid)

