# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database objects for PendingCodeMail"""

__metaclass__ = type
__all__ = ['PendingCodeMail']

from sqlobject import IntCol, StringCol
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad import _
from canonical.launchpad.interfaces import IPendingCodeMail


class PendingCodeMail(SQLBase):

    implements(IPendingCodeMail)

    _table = 'PendingCodeMail'

    id = IntCol(notNull=True)

    rfc2822msgid = StringCol(notNull=True)

    in_reply_to = StringCol()

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_address = StringCol(notNull=True)

    to_address = StringCol(notNull=True)

    subject = StringCol(notNull=True)

    body = StringCol(notNull=True)

    footer = StringCol()

    rationale = StringCol()
