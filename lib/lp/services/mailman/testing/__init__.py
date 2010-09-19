# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test helpers for mailman integration."""

__metaclass__ = type
__all__ = []

import email
from email.mime.text import MIMEText
import os
import shutil

from Mailman import (
    MailList,
    Message,
    mm_cfg,
    )

from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory


class MailmanTestCase(TestCaseWithFactory):
    """TestCase with factory and mailman support."""

    layer = DatabaseFunctionalLayer

    def makeMailmanList(self, lp_mailing_list):
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

    def cleanMailmanList(self, mlist):
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

    def makeMailmanMessage(self, mm_list, sender, subject, content,
                           mime_type='text', attachment=None):
        # Make a Mailman Message.Message.
        if isinstance(sender, (list, tuple)):
            sender = ', '.join(sender)
        message = MIMEText(content, mime_type)
        message['From'] = sender
        message['To'] = mm_list.getListAddress()
        message['Subject'] = subject
        message['Message-ID'] = '<ocelot>'
        mm_message = email.message_from_string(
            message.as_string(), Message.Message)
        if attachment is not None:
            mm_message.attach(attachment, 'octet-stream')
        return mm_message
