# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: d84c3aaa-f65c-49eb-aeea-47ef2bb559c7

__metaclass__ = type

from zope.interface import implements
from canonical.lp import decorates

from canonical.rosetta.interfaces import IRosettaProject
from canonical.database.doap import IProject, IProjects

class RosettaProjects:
    decorates(IProjects)

    def __init__(self, context):
        self.context = context

class RosettaProject:
    implements(IRosettaProject)
    decorates(IProject)

    def __init__(self, context):
        self.context = context

    def poTemplates(self):
        """See IRosettaProject."""
        # A project's templates are the collection of all of the project's
        # products' templates.
        for p in self.context.rosettaProducts():
            for t in p.poTemplates():
                yield t

    def messageCount(self):
        """See IRosettaStats."""
        count = 0
        for p in self.context.rosettaProducts():
            count += p.messageCount()
        return count

    def currentCount(self, language):
        """See IRosettaStats."""
        count = 0
        for p in self.context.rosettaProducts():
            count += p.currentCount(language)
        return count

    def updatesCount(self, language):
        """See IRosettaStats."""
        count = 0
        for p in self.context.rosettaProducts():
            count += p.updatesCount(language)
        return count

    def rosettaCount(self, language):
        """See IRosettaStats."""
        count = 0
        for p in self.context.rosettaProducts():
            count += p.rosettaCount(language)
        return count

