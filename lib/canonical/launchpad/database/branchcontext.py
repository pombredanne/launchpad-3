# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'JunkContext',
    'PackageContext',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchcontext import IBranchContext


class JunkContext:
    implements(IBranchContext)

    name = '+junk'


class PackageContext:
    implements(IBranchContext)

    def __init__(self, distroseries, sourcepackagename):
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename

    @property
    def name(self):
        return '%s/%s/%s' % (
            self.distroseries.distribution.name,
            self.distroseries.name,
            self.sourcepackagename.name)
