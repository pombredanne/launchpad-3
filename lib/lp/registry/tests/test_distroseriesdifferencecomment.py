# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifferenceComment class."""

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceComment,
    IDistroSeriesDifferenceCommentSource,
    )
from lp.testing import TestCaseWithFactory


class DistroSeriesDifferenceCommentTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        # The implementation implements the interface correctly.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()
        # Flush the store to ensure db constraints are triggered.
        Store.of(dsd_comment).flush()

        verifyObject(IDistroSeriesDifferenceComment, dsd_comment)

    def test_comment(self):
        # The comment attribute returns the text of the comment.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment(
            comment="Wait until version 2.3")

        self.assertEqual("Wait until version 2.3", dsd_comment.comment)

    def test_subject(self):
        # The subject of the message is set from the distro series diff
        # title.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()

        self.assertEqual(
            dsd_comment.distro_series_difference.title,
            dsd_comment.message.subject)


class DifferenceCommentSourceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getForDifference(self):
        # Returns all comments for a difference ordered by id.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()
        dsd_comment_2 = self.factory.makeDistroSeriesDifferenceComment(
            dsd_comment.distro_series_difference)
        dsd_other_comment = self.factory.makeDistroSeriesDifferenceComment()

        comment_source = getUtility(IDistroSeriesDifferenceCommentSource)
        comments = comment_source.getForDifference(
            distro_series_difference=dsd_comment.distro_series_difference)

        self.assertEqual([dsd_comment, dsd_comment_2], list(comments))
