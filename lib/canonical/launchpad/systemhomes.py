# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""This module contains the content classes for the 'home pages' of the
subsystems of Launchpad.
"""
__metaclass__ = type

from zope.interface import implements
from canonical.launchpad.interfaces import (
    IDOAPApplication, IFOAFApplication, IMaloneApplication,
    IBazaarApplication)
from canonical.launchpad.database import (Bug, BugWatch, BugExternalRef,
    BugTask, BugTracker)

class DOAPApplication:
    implements(IDOAPApplication)


class FOAFApplication:
    implements(IFOAFApplication)


class MaloneApplication:
    implements(IMaloneApplication)

    def __init__(self):
        self.title = 'Malone: Bug Management in Launchpad'

    @property
    def bug_count(self):
        return Bug.select().count()

    @property
    def bugwatch_count(self):
        return BugWatch.select().count()

    @property
    def bugextref_count(self):
        return BugExternalRef.select().count()

    @property
    def bugtask_count(self):
        return BugTask.select().count()

    @property
    def bugtracker_count(self):
        return BugTracker.select().count()

    @property
    def top_bugtrackers(self):
        result = list(BugTracker.select())
        result.sort(key=lambda a: -a.watchcount)
        return result[:5]

class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'

