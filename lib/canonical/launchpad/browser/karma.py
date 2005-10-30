# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = ['KarmaActionSetNavigation']

from zope.component import getUtility

from canonical.launchpad.interfaces import IKarmaActionSet
from canonical.launchpad.webapp import Navigation


class KarmaActionSetNavigation(Navigation):

    usedfor = IKarmaActionSet

    def traverse(self, name):
        return self.context.getByName(name)

