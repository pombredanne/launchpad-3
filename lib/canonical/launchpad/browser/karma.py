# Copyright 2004 Canonical Ltd

__metaclass__ = type

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.lp.dbschema import KarmaActionCategory
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces import IKarmaActionSet
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView


class KarmaActionSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def actionCategories(self):
        return KarmaActionCategory.items

    def actions(self, actionCategory):
        return getUtility(IKarmaActionSet).selectByCategory(actionCategory)

