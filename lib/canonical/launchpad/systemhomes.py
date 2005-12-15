# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Content classes for the 'home pages' of the subsystems of Launchpad."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements
from canonical.launchpad.interfaces import (
    IRegistryApplication, IFOAFApplication, IMaloneApplication,
    IBazaarApplication, IShipItApplication, IBugSet, IBugWatchSet,
    IBugExternalRefSet, IBugTaskSet, IBugTrackerSet, ILaunchBag,
    BugTaskSearchParams)

class RegistryApplication:
    implements(IRegistryApplication)


class FOAFApplication:
    implements(IFOAFApplication)


class ShipItApplication:
    implements(IShipItApplication)


class MaloneApplication:
    implements(IMaloneApplication)

    def __init__(self):
        self.title = 'Malone: the Launchpad bug tracker'

    @property
    def bug_count(self):
        user = getUtility(ILaunchBag).user
        return getUtility(IBugSet).searchAsUser(user=user).count()

    @property
    def bugwatch_count(self):
        return getUtility(IBugWatchSet).search().count()

    @property
    def bugextref_count(self):
        return getUtility(IBugExternalRefSet).search().count()

    @property
    def bugtask_count(self):
        user = getUtility(ILaunchBag).user
        search_params = BugTaskSearchParams(user=user)
        return getUtility(IBugTaskSet).search(search_params).count()

    @property
    def bugtracker_count(self):
        return getUtility(IBugTrackerSet).search().count()

    @property
    def top_bugtrackers(self):
        return getUtility(IBugTrackerSet).getMostActiveBugTrackers(limit=5)

    @property
    def latest_bugs(self):
        user = getUtility(ILaunchBag).user
        return getUtility(IBugSet).searchAsUser(
            user=user, orderBy='-datecreated', limit=5)


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'
