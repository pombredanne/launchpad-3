# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""GPG Key Information Server Prototype.

It follows the standard URL schema for PKS/SKS systems

It implements the operations:

 - 'index' : returns key index information
 - 'get': returns an ASCII armored public key

It does not depend on GPG; it simply serves the information stored in
files at a given HOME (default to /home/keys/) with the following name
format:

0x<keyid>.<operation>

Example:

$ gpg --list-key cprov > 0x681B6469.index

note: remove the lines containing 'sub' or 'secret' keys

$ gpg --export -a cprov > 0x681B6469.get

"""

__metaclass__ = type

__all__ = [
    'KeyServer',
    'LookUp',
    'SubmitKey',
    'Zeca',
    ]

import os
import cgi

from twisted.web.resource import Resource

from zope.component import getUtility

from canonical.launchpad.interfaces.gpghandler import (
    GPGKeyNotFoundError, IGPGHandler, MoreThanOneGPGKeyFound,
    SecretGPGKeyImportDetected)


GREETING = 'Copyright 2004-2008 Canonical Ltd.\n'


class Zeca(Resource):
    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(
            self, name, request)

    def render_GET(self, request):
        return GREETING


class KeyServer(Zeca):
    def render_GET(self, request):
        return 'Welcome To Fake SKS service.\n'


class LookUp(Resource):
    isLeaf = True
    permitted_actions = ['index', 'get']

    def __init__(self, root):
        Resource.__init__(self)
        self.root = root

    def render_GET(self, request):
        try:
            action = request.args['op'][0]
            keyid = request.args['search'][0]
        except KeyError:
            return 'Invalid Arguments %s' % request.args

        return self.processRequest(action, keyid)

    def processRequest(self, action, keyid):
        if (action not in self.permitted_actions) or not keyid:
            return 'Forbidden: "%s" on ID "%s"' % (action, keyid)

        page = ('<html>\n<head>\n'
                '<title>Results for Key %s</title>\n'
                '</head>\n<body>'
                '<h1>Results for Key %s</h1>\n'
                % (keyid, keyid))

        filename = '%s.%s' % (keyid, action)

        path = os.path.join(self.root, filename)

        try:
            fp = open(path)
        except IOError:
            content = 'Key Not Found'
        else:
            content = cgi.escape(fp.read())
            fp.close()

        page += '<pre>\n%s\n</pre>\n</html>' % content

        return page


SUBMIT_KEY_PAGE = """
<html>
  <head>
    <title>Submit a key</title>
  </head>
  <body>
    <h1>Submit a key</h1>
    <p>%(banner)s</p>
    <form method="post">
      <textarea name="keytext" rows="20" cols="66"></textarea> <br>
      <input type="submit" value="Submit">
    </form>
  </body>
</html>
"""


class SubmitKey(Resource):
    isLeaf = True

    def __init__(self, root):
        Resource.__init__(self)
        self.root = root

    def render_GET(self, request):
        return SUBMIT_KEY_PAGE % {'banner': ''}

    def render_POST(self, request):
        try:
            keytext = request.args['keytext'][0]
        except KeyError:
            return 'Invalid Arguments %s' % request.args
        return self.storeKey(keytext)

    def storeKey(self, keytext):
        gpghandler = getUtility(IGPGHandler)
        try:
            key = gpghandler.importPublicKey(keytext)
        except (GPGKeyNotFoundError, SecretGPGKeyImportDetected,
                MoreThanOneGPGKeyFound), err:
            return SUBMIT_KEY_PAGE % {'banner': str(err)}

        filename = '0x%s.get' % key.fingerprint
        path = os.path.join(self.root, filename)

        fp = open(path, 'w')
        fp.write(keytext)
        fp.close()

        return SUBMIT_KEY_PAGE % {'banner': 'Key added'}
