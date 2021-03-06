# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for testing XML-RPC services."""

__all__ = [
    'XMLRPCTestTransport',
    ]

from cStringIO import StringIO
import httplib
import xmlrpclib

from zope.app.testing.functional import HTTPCaller
from zope.security.management import (
    endInteraction,
    queryInteraction,
    )

from lp.services.webapp.interaction import (
    get_current_principal,
    setupInteraction,
    )


class _FakeSocket(object):
    """Pretend to be a socket that has a makefile method.

    This is used because it is what httplib.HTTPResponse expects.
    """
    def __init__(self, output):
        self._output = output

    def makefile(self, mode='rb', bufsize=0):
        return StringIO(self._output)


class HTTPCallerHTTPConnection(httplib.HTTPConnection):
    """A HTTPConnection which talks to HTTPCaller instead of a real server.

    Only the methods called by xmlrpclib are overridden.
    """

    _data_to_send = ''
    _response = None

    def __init__(self, host):
        httplib.HTTPConnection.__init__(self, host)
        self.caller = HTTPCaller()

    def connect(self):
        """No need to connect."""
        pass

    def send(self, data):
        """Send the request to HTTPCaller."""
        # We don't send it to HTTPCaller yet, we store the data and sends
        # everything at once when the client requests a response.
        self._data_to_send += data

    def _zope_response(self):
        """Get the response."""
        current_principal = None
        # End and save the current interaction, since HTTPCaller creates
        # its own interaction.
        if queryInteraction():
            current_principal = get_current_principal()
            endInteraction()
        if self._response is None:
            self._response = self.caller(self._data_to_send)
        # Restore the interaction to what it was before.
        setupInteraction(current_principal)
        return self._response

    def getresponse(self, buffering=False):
        content = self._zope_response().getOutput()
        sock = _FakeSocket(content)
        response = httplib.HTTPResponse(sock)
        response.begin()
        return response


class XMLRPCTestTransport(xmlrpclib.Transport):
    """An XMLRPC Transport which sends the requests to HTTPCaller."""

    def make_connection(self, host):
        """Return our custom HTTPCaller HTTPConnection."""
        host, self._extra_headers, x509 = self.get_host_info(host)
        return HTTPCallerHTTPConnection(host)
