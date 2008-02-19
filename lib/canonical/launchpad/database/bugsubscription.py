# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IBugSubscription
from canonical.launchpad.validators.person import public_person_validator


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table = 'BugSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person',
                        notNull=True, validator=public_person_validator)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        validator=public_person_validator, notNull=True)

    @property
    def display_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Subscribed themselves'
        else:
            return u'Subscribed by %s' % self.subscribed_by.displayname
