# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['ParsedApacheLog']

from storm.locals import (
    Int,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.apachelogparser.interfaces.parsedapachelog import (
    IParsedApacheLog,
    )


class ParsedApacheLog(Storm):
    """See `IParsedApacheLog`"""

    implements(IParsedApacheLog)
    __storm_table__ = 'ParsedApacheLog'

    id = Int(primary=True)
    first_line = Unicode(allow_none=False)
    bytes_read = Int(allow_none=False)
    date_last_parsed = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    def __init__(self, first_line, bytes_read):
        super(ParsedApacheLog, self).__init__()
        self.first_line = unicode(first_line)
        self.bytes_read = bytes_read
        getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR).add(self)
