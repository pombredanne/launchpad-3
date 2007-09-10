""" Copyright 2004 Canonical Ltd.  All rights reserved.

GPG Key Information Server Prototype.

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

__all__ = ['Zeca', 'KeyServer', 'LookUp']

import os
import cgi

from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor

GREETING = 'Copyright 2004-2005 Canonical Ltd.\n'


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
        # XXX cprov 2005-05-13:
        # WTF is that way to recover the HTTP GET attributes
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


if __name__ == "__main__":
    from canonical.config import config

    root = config.zeca.root

    zeca = Zeca()
    keyserver = KeyServer()
    keyserver.putChild('lookup', LookUp(root))
    zeca.putChild('pks', keyserver)

    site = server.Site(zeca)
    reactor.listenTCP(11371, site)
    reactor.run()

