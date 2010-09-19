# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the lpmoderate monekypatches"""

from __future__ import with_statement

__metaclass__ = type
__all__ = []

from Mailman import Errors
from Mailman.Handlers import LPModerate

from canonical.testing import DatabaseFunctionalLayer

from lp.services.mailman.testing import MailmanTestCase


class TestLPModerateTestCase(MailmanTestCase):
    """Test lpmoderate."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLPModerateTestCase, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = self.makeMailmanList(self.mailing_list)

    def tearDown(self):
        super(TestLPModerateTestCase, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    def test_hold_discard_empty_mesage(self):
        spam_message = self.makeMailmanMessage(
            self.mm_list, 'spammer@spam.dom',
            'get drugs', '<a><img /></a>.', mime_type='html')
        args = (self.mm_list, spam_message, {}, 'Not subscribed')
        self.assertRaises(
            Errors.DiscardMessage, LPModerate.hold, *args)
