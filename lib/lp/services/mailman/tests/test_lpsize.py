# Copyright 20010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the lpsize monekypatches"""

from __future__ import with_statement

__metaclass__ = type
__all__ = []

from email.mime.application import MIMEApplication

from Mailman import Errors
from Mailman.Handlers import LPSize

from canonical.config import config
from canonical.testing import LaunchpadFunctionalLayer
from lp.services.mailman.testing import MailmanTestCase


class TestLPSizeTestCase(MailmanTestCase):
    """Test LPSize.

    Mailman process() methods quietly return. They may set msg_data key-values
    or raise an error to end processing. This group of tests tests often check
    for errors, but that does not mean there is an error condition, it only
    means message processing has reached a final decision. Messages that do
    not cause a final decision pass-through and the process() methods ends
    without a return.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestLPSizeTestCase, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = self.makeMailmanList(self.mailing_list)
        self.subscriber = self.team.teamowner
        self.subscriber_email = self.team.teamowner.preferredemail.email

    def tearDown(self):
        super(TestLPSizeTestCase, self).tearDown()
        self.cleanMailmanList(self.mm_list)

    def test_process_size_under_soft_limit(self):
        # Any message under 40kb is sent to the list.
        attachment = MIMEApplication(
            '\n'.join(['x' * 20] * 1000), 'octet-stream')
        message = self.makeMailmanMessage(
            self.mm_list, self.subscriber_email, 'subject', 'content',
            attachment=attachment)
        msg_data = {}
        silence = LPSize.process(self.mm_list, message, msg_data)
        self.assertEqual(None, silence)

    def test_process_size_over_soft_limit_held(self):
        # Messages over 40km held for moderation.
        self.assertEqual(40000, config.mailman.soft_max_size)
        attachment = MIMEApplication(
            '\n'.join(['x' * 40] * 1000), 'octet-stream')
        message = self.makeMailmanMessage(
            self.mm_list, self.subscriber_email, 'subject', 'content',
            attachment=attachment)
        msg_data = {}
        args = (self.mm_list, message, msg_data)
        self.assertRaises(
            Errors.HoldMessage, LPSize.process, *args)
        self.assertEqual(1, self.mailing_list.getReviewableMessages().count())

    def test_process_size_over_hard_limit_discarded(self):
        # Messages over 1MB are discarded.
        self.assertEqual(1000000, config.mailman.hard_max_size)
        attachment = MIMEApplication(
            '\n'.join(['x' * 1000] * 1000), 'octet-stream')
        message = self.makeMailmanMessage(
            self.mm_list, self.subscriber_email, 'subject', 'content',
            attachment=attachment)
        msg_data = {}
        args = (self.mm_list, message, msg_data)
        self.assertRaises(
            Errors.DiscardMessage, LPSize.process, *args)
        self.assertEqual(0, self.mailing_list.getReviewableMessages().count())
