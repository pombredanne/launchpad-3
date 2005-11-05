# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'KarmaActionEditView',
    'KarmaActionSetNavigation',
    ]

from canonical.launchpad.interfaces import IKarmaActionSet
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import Navigation, canonical_url


class KarmaActionSetNavigation(Navigation):

    usedfor = IKarmaActionSet

    def traverse(self, name):
        return self.context.getByName(name)


class KarmaActionEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


