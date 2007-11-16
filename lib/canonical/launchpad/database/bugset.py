# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSetBase']

from zope.interface import implements
from zope.app.form.browser.interfaces import IAddFormCustomization
from canonical.launchpad.interfaces import IBugSet, NotFoundError

class BugSetBase:
    implements(IBugSet, IAddFormCustomization)

    def __init__(self, bug=None):
        self.bug = bug
        self.title = 'Malone: the Launchpad bug tracker'

    def __getitem__(self, id):
        item = self.table.selectOne(self.table.q.id == id)
        if item is None:
            raise NotFoundError(id)
        return item

    def __iter__(self):
        for row in self.table.select(self.table.q.bugID == self.bug):
            yield row

    def add(self, ob):
        return ob

    def nextURL(self):
        return '.'

