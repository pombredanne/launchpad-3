# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database objects for PendingCodeMail"""

__metaclass__ = type
__all__ = ['PendingCodeMail', 'PendingCodeMailSource']


from calendar import timegm
from email.Message import Message
from email.Utils import formatdate

from sqlobject import IntCol, StringCol
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IPendingCodeMail, IPendingCodeMailSource)
from canonical.launchpad.mailout import append_footer
from canonical.launchpad.mail.sendmail import sendmail


class PendingCodeMail(SQLBase):

    implements(IPendingCodeMail)

    _table = 'PendingCodeMail'

    id = IntCol(notNull=True)

    rfc822msgid = StringCol(notNull=True)

    in_reply_to = StringCol()

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_address = StringCol(notNull=True)

    reply_to_address = StringCol()

    to_address = StringCol(notNull=True)

    subject = StringCol(notNull=True)

    body = StringCol(notNull=True)

    footer = StringCol()

    rationale = StringCol()

    branch_url = StringCol()

    branch_project_name = StringCol()

    def toMessage(self):
        mail = Message()
        mail['Message-Id'] = self.rfc822msgid
        if self.in_reply_to is not None:
            mail['In-Reply-To'] = self.in_reply_to
        mail['To'] = self.to_address
        mail['From'] = self.from_address
        if self.reply_to_address is not None:
            mail['Reply-To'] = self.reply_to_address
        mail['X-Launchpad-Message-Rationale'] = self.rationale
        mail['X-Launchpad-Branch'] = self.branch_url
        if self.branch_project_name is not None:
            mail['X-Launchpad-Project'] = self.branch_project_name
        mail['Subject'] = self.subject
        mail['Date'] = formatdate(timegm(self.date_created.utctimetuple()))
        mail.set_payload(append_footer(self.body, self.footer))
        return mail

    def sendMail(self):
        sendmail(self.toMessage())
        self.destroySelf()


class PendingCodeMailSource:

    implements(IPendingCodeMailSource)

    def create(self, from_address, reply_to_address, to_address, rationale,
               branch_url, branch_project_name, subject, body, footer,
               message_id):
        """See `IPendingCodeMailSource`"""
        return PendingCodeMail(from_address=from_address,
            reply_to_address=reply_to_address, to_address=to_address,
            rationale=rationale, branch_url=branch_url,
            branch_project_name=branch_project_name, subject=subject,
            body=body, footer=footer, rfc822msgid=message_id)
