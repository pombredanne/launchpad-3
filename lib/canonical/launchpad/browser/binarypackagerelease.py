# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BinaryPackageReleaseNavigation',
    'BinaryPackageView',
    ]

from apt_pkg import ParseDepends

from canonical.launchpad.browser.packagerelationship import (
    PackageRelationship, relationship_builder)
from canonical.launchpad.interfaces import IBinaryPackageRelease
from canonical.launchpad.webapp import Navigation

class BinaryPackageReleaseNavigation(Navigation):
    usedfor = IBinaryPackageRelease


class BinaryPackageView:
    """View class for BinaryPackage"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _relationship_parser(self, content):
        """Wrap the relationship_builder for BinaryPackages.

        Define apt_pkg.ParseDep as a relationship 'parser' and
        IDistroArchSeries.getBinaryPackage as 'getter'.
        """
        getter = self.context.build.distroarchseries.getBinaryPackage
        parser = ParseDepends
        return relationship_builder(content, parser=parser, getter=getter)

    def depends(self):
        return self._relationship_parser(self.context.depends)

    def recommends(self):
        return self._relationship_parser(self.context.recommends)

    def conflicts(self):
        return self._relationship_parser(self.context.conflicts)

    def replaces(self):
        return self._relationship_parser(self.context.replaces)

    def suggests(self):
        return self._relationship_parser(self.context.suggests)

    def provides(self):
        return self._relationship_parser(self.context.provides)
