from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.launchpad.database import RevisionAuthor
from canonical.testing import LaunchpadZopelessLayer


class TestRevisionAuthor(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

    def testGetNameWithoutEmailReturnsNamePart(self):
        # getNameWithoutEmail returns the 'name' part of the revision author
        # information.
        author = RevisionAuthor(name=u'Jonathan Lange <jml@canonical.com>')
        self.assertEqual(u'Jonathan Lange', author.getNameWithoutEmail())

    def testGetNameWithoutEmailWithNoName(self):
        # If there is no name in the revision author information,
        # getNameWithoutEmail returns None.
        author = RevisionAuthor(name=u'jml@mumak.net')
        self.assertEqual(None, author.getNameWithoutEmail())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
