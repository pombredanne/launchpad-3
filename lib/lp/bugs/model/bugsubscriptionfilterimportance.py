# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscriptionFilterImportance']

from storm.locals import (
    Int,
    Reference,
    )

from canonical.database.enumcol import DBEnum
from lp.bugs.interfaces.bugtask import BugTaskImportance
from lp.services.database.stormbase import StormBase


class BugSubscriptionFilterImportance(StormBase):
    """Importances to filter."""

    __storm_table__ = "BugSubscriptionFilterImportance"

    id = Int(primary=True)

    filter_id = Int("filter", allow_none=False)
    filter = Reference(filter_id, "BugSubscriptionFilter.id")

    importance = DBEnum(enum=BugTaskImportance, allow_none=False)
