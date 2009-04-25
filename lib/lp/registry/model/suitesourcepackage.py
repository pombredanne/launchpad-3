# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of `ISuiteSourcePackage`."""

__metaclass__ = type
__all__ = [
    'SuiteSourcePackage',
    ]


class SuiteSourcePackage:
    """Implementation of `ISuiteSourcePackage`."""

    def __init__(self, distroseries, pocket, sourcepackagename):
        self.distroseries = distroseries
        self.pocket = pocket
        self.sourcepackagename = sourcepackagename

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.path)

    @property
    def distribution(self):
        return self.distroseries.distribution

    @property
    def path(self):
        return '/'.join([
            self.distribution.name,
            self.suite,
            self.sourcepackagename.name])

    @property
    def sourcepackage(self):
        return self.distroseries.getSourcePackage(self.sourcepackagename)

    @property
    def suite(self):
        return self.distroseries.getSuite(self.pocket)
