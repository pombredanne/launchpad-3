# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

from canonical.launchpad.ftests import login
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestBugIndexedMessages(TestCaseWithFactory):
    """Test the workings of IBug.indexed_messages."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugIndexedMessages, self).setUp()
        login('foo.bar@canonical.com')

        bug_1 = self.factory.makeBug()
        self.bug_2 = self.factory.makeBug()

        message_1 = self.factory.makeMessage()
        message_2 = self.factory.makeMessage()
        message_2.parent = message_1

        bug_1.linkMessage(message_1)
        self.bug_2.linkMessage(message_2)

    def test_indexed_message_null_parents(self):
        # Accessing the parent of an IIndexedMessage will return None if
        # the parent isn't linked to the same bug as the
        # IIndexedMessage.
        for indexed_message in self.bug_2.indexed_messages:
            self.failUnlessEqual(None, indexed_message.parent)
