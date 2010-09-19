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

    def test_process_message_from_preapproved(self):
        # Mailman process methods quietly return. They may set message data
        # to raise an error for other handlers to process.
        message = self.makeMailmanMessage(
            self.mm_list, 'lp-user@place.dom', 'subject', 'any content.')
        msg_data = dict(approved=True)
        silence = LPModerate.process(self.mm_list, message, msg_data)
        self.assertEqual(None, silence)

    def test_process_message_from_subscriber(self):
        # Mailman process methods quietly return. They may set message data
        # to raise an error for other handlers to process.
        subscriber_email = self.team.teamowner.preferredemail.email
        message = self.makeMailmanMessage(
            self.mm_list, subscriber_email, 'subject', 'any content.')
        msg_data = dict(approved=False)
        silence = LPModerate.process(self.mm_list, message, msg_data)
        self.assertEqual(None, silence)

    def test_process_empty_mesage_from_nonsubcriber_discarded(self):
        spam_message = self.makeMailmanMessage(
            self.mm_list, 'lp-user@place.dom',
            'get drugs', '<a><img /></a>.', mime_type='html')
        msg_data = dict(approved=False)
        args = (self.mm_list, spam_message, msg_data)
        self.assertRaises(
            Errors.DiscardMessage, LPModerate.process, *args)
