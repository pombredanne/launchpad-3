# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.testing import TestCase
from lp.services.mail.handlers import MailHandlers


class TestMailHandlers(TestCase):

    def test_get(self):
        handlers = MailHandlers()
        self.assertIsNot(None, handlers.get("bugs.launchpad.net"))
        self.assertIs(None, handlers.get("no.such.domain"))

    def test_add_for_new_domain(self):
        handlers = MailHandlers()
        self.assertIs(None, handlers.get("some.domain"))
        handler = object()
        handlers.add("some.domain", handler)
        self.assertIs(handler, handlers.get("some.domain"))

    def test_add_for_existing_domain(self):
        # When adding a new handler for a already congfigured domain, the
        # existing handler is overwritten.
        handlers = MailHandlers()
        handler1 = object()
        handlers.add("some.domain", handler1)
        handler2 = object()
        handlers.add("some.domain", handler2)
        self.assertIs(handler2, handlers.get("some.domain"))
