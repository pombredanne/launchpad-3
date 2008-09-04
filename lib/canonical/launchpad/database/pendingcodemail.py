# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database objects for PendingCodeMail"""

__metaclass__ = type
__all__ = ['PendingCodeMail']


from email.Message import Message

from sqlobject import IntCol, StringCol
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad import _
from canonical.launchpad.interfaces import IPendingCodeMail
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

    to_address = StringCol(notNull=True)

    subject = StringCol(notNull=True)

    body = StringCol(notNull=True)

    footer = StringCol()

    rationale = StringCol()

    branch_url = StringCol()

    def toMessage(self):
        mail = Message()
        mail['Message-Id'] = self.rfc822msgid
        mail['To'] = self.to_address
        mail['From'] = self.from_address
        mail['X-Launchpad-Message-Rationale'] = self.rationale
        mail['X-Launchpad-Branch'] = self.branch_url
        mail['Subject'] = self.subject
        mail.set_payload(append_footer(self.body, self.footer))
        return mail

    def sendMail(self):
        sendmail(self.toMessage())
