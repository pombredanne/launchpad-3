# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Zope interfaces
from zope.interface import implements

# canonical imports
from canonical.launchpad.interfaces import IKarmaPointsManager

from canonical.lp.dbschema import KarmaType

# XXX: These points are totally *CRAP*.
KARMA_POINTS = {KarmaType.BUG_REPORT: 10,
                KarmaType.BUG_FIX: 20,
                KarmaType.BUG_COMMENT: 5,
                KarmaType.WIKI_EDIT: 2,
                KarmaType.WIKI_CREATE: 3,
                KarmaType.PACKAGE_UPLOAD: 10}


class KarmaPointsManager:
    implements(IKarmaPointsManager)

    def getPoints(self, karmatype):
        return KARMA_POINTS[karmatype]

    def queryPoints(self, karmatype, default=None):
        try:
            return KARMA_POINTS[karmatype]
        except KeyError:
            return default

