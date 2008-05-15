# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadFunctionalLayer
from zope.testing.doctestunit import DocTestSuite

from canonical.launchpad.database import Message
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory


class TestMessage(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def createTestMessages(self):
        message1 = self.factory.makeMessage()
        message2 = self.factory.makeMessage(parent=message1)
        message3 = self.factory.makeMessage(parent=message1)
        message4 = self.factory.makeMessage(parent=message2)
        return (message1, message2, message3, message4)

    def test_parentToChild(self):
        messages = self.createTestMessages()
        message1, message2, message3, message4 = messages
        expected = {
            message1: [message2, message3],
            message2: [message4],
            message3: [], message4:[]}
        result, roots = Message._parentToChild(messages)
        self.assertEqual(expected, result)
        self.assertEqual([message1], roots)

    def test_threadMessages(self):
        messages = self.create_test_messages()
        message1, message2, message3, message4 = messages
        threads = Message.threadMessages(messages)
        self.assertEqual(
            [(message1, [(message2, [(message4, [])]), (message3, [])])],
            threads)

    def test_flattenThreads(self):
        messages = self.create_test_messages()
        message1, message2, message3, message4 = messages
        threads = Message.threadMessages(messages)
        flattened = list(Message.flattenThreads(threads))
        expected = [(0, message1),
                    (1, message2),
                    (2, message4),
                    (1, message3)]
        self.assertEqual(expected, flattened)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.database.message'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())

