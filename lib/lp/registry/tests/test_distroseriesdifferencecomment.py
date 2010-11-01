# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifferenceComment class."""

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import DatabaseFunctionalLayer
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

    def test_body_text(self):
        # The comment attribute returns the text of the comment.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment(
            comment="Wait until version 2.3")

        self.assertEqual("Wait until version 2.3", dsd_comment.body_text)

    def test_subject(self):
        # The subject of the message is set from the distro series diff
        # title.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()

        self.assertEqual(
            dsd_comment.distro_series_difference.title,
            dsd_comment.message.subject)

    def test_comment_author(self):
        # The comment author just proxies the author from the message.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()

        self.assertEqual(
            dsd_comment.message.owner, dsd_comment.comment_author)

    def test_comment_date(self):
        # The comment date attribute just proxies from the message.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()

        self.assertEqual(
            dsd_comment.message.datecreated, dsd_comment.comment_date)

    def test_getForDifference(self):
        # The utility can get comments by id.
        dsd_comment = self.factory.makeDistroSeriesDifferenceComment()
        Store.of(dsd_comment).flush()

        comment_src = getUtility(IDistroSeriesDifferenceCommentSource)
        self.assertEqual(
            dsd_comment, comment_src.getForDifference(
                dsd_comment.distro_series_difference, dsd_comment.id))
