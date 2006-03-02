# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View classes related to ISourcePackage."""

__metaclass__ = type

__all__ = ['BinaryPackageView']

from apt_pkg import ParseDepends

from zope.component import getUtility
from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    ILaunchBag, IBugTaskSearch, BugTaskSearchParams, IBugSet,
    UNRESOLVED_BUGTASK_STATUSES, NotFoundError
    )
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.browser.packagerelationship import PackageRelationship

class BinaryPackageView:
    """View class for BinaryPackage"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.launchbag = getUtility(ILaunchBag)

    def _relationships(self, string):
        if not string:
            return []

        relationships = [L[0] for L in ParseDepends(string)]
        return [
            PackageRelationship(name, signal, version)
            for name, version, signal in relationships
            ]

    def depends(self):
        return self._relationships(self.context.depends)

    def recommends(self):
        return self._relationships(self.context.recommends)

    def conflicts(self):
        return self._relationships(self.context.conflicts)

    def replaces(self):
        return self._relationships(self.context.replaces)

    def suggests(self):
        return self._relationships(self.context.suggests)

    def provides(self):
        return self._relationships(self.context.provides)

