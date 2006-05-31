# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LaunchpadStatistic', 'LaunchpadStatisticSet']

from email.Utils import make_msgid

from zope.interface import implements
from zope.component import getUtility

from sqlobject import IntCol, StringCol
from canonical.launchpad import _
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import (
    ILaunchpadStatistic, ILaunchpadStatisticSet)
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.pomsgid import POMsgID


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

    def updateStatistics(self, ztm):
        """See ILaunchpadStatisticSet."""
        self._updateRosettaStatistics(ztm)
        # ... add more update calls here.
        # TODO: SteveAlexander, 2006-05-30

    def _updateRosettaStatistics(self, ztm):
        self.update('potemplate_count', POTemplate.select().count())
        ztm.commit()
        self.update('pofile_count', POFile.select().count())
        ztm.commit()
        self.update('pomsgid_count', POMsgID.select().count())
        ztm.commit()
        self.update('translator_count', Person.select(
            "POSubmission.person=Person.id",
            clauseTables=['POSubmission'],
            distinct=True).count())
        ztm.commit()
        self.update('language_count', Language.select(
            "POFile.language=Language.id",
            clauseTables=['POFile'],
            distinct=True).count())
        ztm.commit()

