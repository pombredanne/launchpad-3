# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""In-process keyserver fixture tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.twistedsupport import (
    AsynchronousDeferredRunTestForBrokenTwisted,
    )
from twisted.internet import defer
from twisted.web.client import getPage

from lp.services.config import config
from lp.testing import TestCase
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.keyserver.web import GREETING


class TestInProcessKeyServerFixture(TestCase):

    run_tests_with = AsynchronousDeferredRunTestForBrokenTwisted.make_factory(
        timeout=10)

    @defer.inlineCallbacks
    def test_url(self):
        # The url is the one that gpghandler is configured to hit.
        fixture = self.useFixture(InProcessKeyServerFixture())
        yield fixture.start()
        self.assertEqual(
            ("http://%s:%d" % (
                config.gpghandler.host,
                config.gpghandler.port)).encode("UTF-8"),
            fixture.url)

    @defer.inlineCallbacks
    def test_starts_properly(self):
        # The fixture starts properly and we can load the page.
        fixture = self.useFixture(InProcessKeyServerFixture())
        yield fixture.start()
        content = yield getPage(fixture.url)
        self.assertEqual(GREETING, content)
