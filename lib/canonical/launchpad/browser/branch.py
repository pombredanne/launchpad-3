# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch
from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import canonical_url

__all__ = [
    'BranchEditView',
    ]


class BranchEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))
