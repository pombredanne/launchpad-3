# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""In-process keyserver fixture."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'InProcessKeyServerFixture',
    ]

from textwrap import dedent

from fixtures import (
    Fixture,
    TempDir,
    )
from twisted.internet import (
    defer,
    endpoints,
    reactor,
    )
from twisted.python.compat import nativeString
from twisted.web import server

from lp.services.config import config
from lp.testing.keyserver.web import KeyServerResource


class InProcessKeyServerFixture(Fixture):
    """A fixture that runs an in-process key server.

    This is much faster than the out-of-process `KeyServerTac`, but it can
    only be used if all the tests relying on it are asynchronous.

    Users of this fixture must call the `start` method, which returns a
    `Deferred`, and arrange for that to get back to the reactor.  This is
    necessary because the basic fixture API does not allow `setUp` to return
    anything.  For example:

        class TestSomething(TestCase):

            run_tests_with = AsynchronousDeferredRunTest.make_factory(
                timeout=10)

            @defer.inlineCallbacks
            def setUp(self):
                super(TestSomething, self).setUp()
                yield self.useFixture(InProcessKeyServerFixture()).start()
    """

    @defer.inlineCallbacks
    def start(self):
        resource = KeyServerResource(self.useFixture(TempDir()).path)
        endpoint = endpoints.serverFromString(reactor, nativeString("tcp:0"))
        port = yield endpoint.listen(server.Site(resource))
        self.addCleanup(port.stopListening)
        config.push("in-process-key-server-fixture", dedent("""
            [gpghandler]
            port: %s
            """) % port.getHost().port)
        self.addCleanup(config.pop, "in-process-key-server-fixture")

    @property
    def url(self):
        """The URL that the web server will be running on."""
        return ("http://%s:%d" % (
            config.gpghandler.host, config.gpghandler.port)).encode("UTF-8")
