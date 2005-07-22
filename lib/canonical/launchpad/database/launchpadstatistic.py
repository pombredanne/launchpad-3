# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LaunchpadStatistic', 'LaunchpadStatisticSet']

from email.Utils import make_msgid

from zope.interface import implements
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from sqlobject import IntCol, StringCol
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    ILaunchpadStatistic, ILaunchpadStatisticSet)
from canonical.database.sqlbase import SQLBase

class LaunchpadStatistic(SQLBase):
    """A table of Launchpad Statistics."""

    implements(ILaunchpadStatistic)

    _table = 'LaunchpadStatistic'

    # db field names
    name = StringCol(notNull=True, alternateID=True, unique=True)
    value = IntCol(notNull=True)
    dateupdated = UtcDateTimeCol(notNull=True, default=UTC_NOW)


class LaunchpadStatisticSet:
    """See canonical.launchpad.interfaces.ILaunchpadStatisticSet."""

    implements(ILaunchpadStatisticSet)

    def update(self, name, value):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            stat = LaunchpadStatistic(name=name, value=value)
        else:
            stat.value = value
            stat.dateupdated = UTC_NOW

    def dateupdated(self, name):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            return None
        return stat.dateupdated

    def value(self, name):
        """See ILaunchpadStatisticSet."""
        stat = LaunchpadStatistic.selectOneBy(name=name)
        if stat is None:
            return None
        return stat.value


