from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.launchpad.database import RevisionAuthor
from canonical.testing import LaunchpadZopelessLayer


class TestRevisionAuthor(TestCase):
    """Unit tests for the RevisionAuthor database class."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

    def testGetNameWithoutEmailReturnsNamePart(self):
        # name_without_email is equal to the 'name' part of the revision author
        # information.
        author = RevisionAuthor(name=u'Jonathan Lange <jml@canonical.com>')
        self.assertEqual(u'Jonathan Lange', author.name_without_email)

    def testGetNameWithoutEmailWithNoName(self):
        # If there is no name in the revision author information,
        # name_without_email is an empty string.
        author = RevisionAuthor(name=u'jml@mumak.net')
        self.assertEqual('', author.name_without_email)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
