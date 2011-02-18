# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscriptionFilterTag']

from storm.locals import (
    Bool,
    Int,
    Reference,
    Unicode,
    )

from lp.services.database.stormbase import StormBase


class BugSubscriptionFilterTag(StormBase):
    """Tags to filter."""

    __storm_table__ = "BugSubscriptionFilterTag"

    id = Int(primary=True)

    filter_id = Int("filter", allow_none=False)
    filter = Reference(filter_id, "BugSubscriptionFilter.id")

    include = Bool(allow_none=False)
    tag = Unicode(allow_none=False)

    @property
    def qualified_tag(self):
        """The tag qualified with a hyphen if it is to be omitted."""
        if self.include:
            return self.tag
        else:
            return u"-" + self.tag
