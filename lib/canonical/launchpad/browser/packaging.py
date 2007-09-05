# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'PackagingAddView',
    ]

from zope.app.form.interfaces import WidgetsError
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import IPackagingUtil, ILaunchBag
from canonical.launchpad.webapp import canonical_url, GeneralFormView

class PackagingAddView(GeneralFormView):

    def initialize(self):
        self.top_of_page_errors = []

    def validate(self, form_values):
        productseries = self.context
        sourcepackagename = form_values['sourcepackagename']
        distroseries = form_values['distroseries']
        packaging = form_values['packaging']

        util = getUtility(IPackagingUtil)
        if util.packagingEntryExists(
            productseries, sourcepackagename, distroseries):
            self.top_of_page_errors.append(_(
                "This series is already packaged in %s" %
                distroseries.displayname))
            raise WidgetsError(self.top_of_page_errors)

    def process(self, distroseries, sourcepackagename, packaging):
        # get the user
        user = getUtility(ILaunchBag).user
        productseries = self.context

        # Invoke utility to create a packaging entry
        util = getUtility(IPackagingUtil)
        util.createPackaging(
            productseries, sourcepackagename, distroseries,
            packaging, owner=user)

    def nextURL(self):
        return canonical_url(self.context)
