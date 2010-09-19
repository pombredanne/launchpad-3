# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the lpmoderate monekypatches"""

from __future__ import with_statement

__metaclass__ = type
__all__ = []

import email
from email.mime.text import MIMEText
import os
import shutil

from Mailman import (
    Errors,
    MailList,
    Message,
    mm_cfg,
    )
from Mailman.Handlers import LPModerate

from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory


def makeMailmanList(lp_mailing_list):
    # This utility is based on mailman/tests/TestBase.py.
    mlist = MailList.MailList()
    team = lp_mailing_list.team
    owner_email = team.teamowner.preferredemail.email
    mlist.Create(team.name, owner_email, 'password')
    mlist.host_name = 'launchpad.dev'
    mlist.web_page_url = 'http://lists.launchpad.dev/mailman/'
    mlist.Save()
    mlist.addNewMember(owner_email)
    return mlist


def cleanMailmanList(mlist):
    # This utility is based on mailman/tests/TestBase.py.
    mlist.Unlock()
    listname = mlist.internal_name()
    for dirtmpl in ['lists/%s',
                    'archives/private/%s',
                    'archives/private/%s.mbox',
                    'archives/public/%s',
                    'archives/public/%s.mbox',
                    ]:
        list_dir = os.path.join(mm_cfg.VAR_PREFIX, dirtmpl % listname)
        if os.path.islink(list_dir):
            os.unlink(list_dir)
        elif os.path.isdir(list_dir):
            shutil.rmtree(list_dir)


def makeMailmanMessage(mm_list, sender, subject, content, mime_type='text'):
        if isinstance(sender, (list, tuple)):
            sender = ', '.join(sender)
        message = MIMEText(content, mime_type)
        message['From'] = sender
        message['To'] = mm_list.getListAddress()
        message['Subject'] = subject
        message['Message-ID'] = '<ocelot>'
        return email.message_from_string(message.as_string(), Message.Message)


class TestLPModerateTestCase(TestCaseWithFactory):
    """Test lpmoderate."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLPModerateTestCase, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = makeMailmanList(self.mailing_list)

    def tearDown(self):
        super(TestLPModerateTestCase, self).tearDown()
        cleanMailmanList(self.mm_list)

    def test_hold_discard_empty_mesage(self):
        spam_message = makeMailmanMessage(
            self.mm_list, 'spammer@spam.dom',
            'get drugs', '<a><img /></a>.', mime_type='html')
        args = (self.mm_list, spam_message, {}, 'Not subscribed')
        self.assertRaises(
            Errors.DiscardMessage, LPModerate.hold, *args)
