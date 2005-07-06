# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['GpgHandler', 'PymeSignature', 'PymeKey']

# standard
import os
import shutil
import urllib
import urllib2
import re

# launchpad
from canonical.config import config

# validators
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.gpg import valid_fingerprint
from canonical.launchpad.validators.gpg import valid_keyid

# zope
from zope.interface import implements
from zope.component import getUtility

# interface
from canonical.launchpad.interfaces import (
    IGpgHandler, IPymeSignature, IPymeKey)

# pyme
import pyme.core


class GpgHandler:
    """See IGpgHandler."""

    implements(IGpgHandler)

    def __init__(self):
        """Initialize environment variable."""
        self.home = config.gpghandler.home
        self._setHome()
        os.environ['GNUPGHOME'] = self.home

    # XXX cprov 20050516
    # Is not thread safe ... should it be ?
    def _setHome(self):
        """Recreate the directory and the configuration file."""
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
    def verifySignature(self, content, signature=None, key=None):
        """See IGpgHandler."""

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
            sig = pyme.core.Data(signature.encode('ascii'))
            # store the content
            plain = pyme.core.Data(content.encode('ascii'))
            # process it
            c.op_verify(sig, plain, None)
        else:
            # store clearsigned signature
            sig = pyme.core.Data(content.encode('ascii'))
            # writeable content
            plain = pyme.core.Data()
            # process it
            c.op_verify(sig, None, plain)

        result = c.op_verify_result()

        # XXX cprov 20050328
        # it doesn't support multiple signatures yet
        signature = result.signatures

        # signature.status == 0 means "Ok"
        if signature.status != 0:
            # return an empty signature object
            return PymeSignature()

        fingerprint = signature.fpr
        plain.seek(0, 0)
        plain_data = plain.read()

        # return the signature container
        return PymeSignature(fingerprint=fingerprint, plain_data=plain_data)


    def importPubKey(self, pubkey):
        """See IGpgHandler."""
        c = pyme.core.Context()
        c.set_armor(1)

        newkey = pyme.core.Data(pubkey)
        c.op_import(newkey)
        result = c.op_import_result()

        # no key was imported
        if result.considered == 0:
            return

        fingerprint = result.imports.fpr

        key = PymeKey(fingerprint)

        # pubkey not recognized
        if key == None:
            return

        return key

    def getKeyIndex(self, fingerprint):
        """See IGpgHandler for further information."""
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

    def getPubKey(self, fingerprint):
        """See IGpgHandler for further information."""
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
            return False, 'URLError: %s at %s' % (e.reason, url)
        except urllib2.HTTPError, e:
            return False, 'HTTPError: %s at %s' % (e.msg, url)

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
        key = c.get_key(fingerprint.encode('ascii'), 0)

        if valid_fingerprint(key.subkeys.fpr):
            self.fingerprint = key.subkeys.fpr
        else:
            self.fingerprint = None
        self.algorithm = key.subkeys.pubkey_algo
        self.revoked = key.subkeys.revoked
        self.keysize = key.subkeys.length

        if fingerprint is not None and valid_keyid(key.subkeys.fpr[-8:]):
            self.keyid = key.subkeys.fpr[-8:]
        else:
            self.keyid = None
        # copy the UIDs 
        self.uids = []
        uid = key.uids
        while uid:
            if valid_email(uid.uid) and not uid.revoked:
                self.uids.append(uid.uid)
            uid = uid.next
