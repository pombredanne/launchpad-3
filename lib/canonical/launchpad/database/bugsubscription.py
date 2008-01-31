# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IBugSubscription, IHasLinkTo


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table = 'BugSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person', notNull=True)

    def _set_person(self, value):
        if IHasLinkTo.providedBy(value):
            value.linkTo(self)
        self._SO_set_person(value)

    def _set_subscribed_by(self, value):
        if IHasLinkTo.providedBy(value):
            value.linkTo(self)
        self._SO_set_subscribed_by(value)

    def __init__(self, bug, person, subscribed_by):
        if IHasLinkTo.providedBy(person):
            person.linkTo(self)
        super(BugSubscription, self).__init__(bug, person, subscribed_by)

    @property
    def display_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Subscribed themselves'
        else:
            return u'Subscribed by %s' % self.subscribed_by.displayname
