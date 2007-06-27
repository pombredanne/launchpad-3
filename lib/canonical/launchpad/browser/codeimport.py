# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Broswer views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    'CodeImportView',
    ]


from canonical.launchpad import _
from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView, Navigation
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import LaunchpadDropdownWidget

from zope.app.form import CustomWidgetFactory
from zope.schema import Choice

import operator


class CodeImportSetNavigation(Navigation):

    usedfor = ICodeImportSet

    def breadcrumb(self):
        return "Code Imports"

    def traverse(self, id):
        try:
            return self.context.get(id)
        except LookupError:
            return None


class CodeImportSetView(LaunchpadView):
    def initialize(self):
        # ICodeImport['review_status'].required is True, which means the
        # generated <select> widget lacks a 'no choice' option.
        field = Choice(
            __name__='status', title=_("Review Status"),
            vocabulary='CodeImportReviewStatus', required=False)
        factory = CustomWidgetFactory(LaunchpadDropdownWidget)
        self.status_widget = factory(field.bind(self.context), self.request)
        self.status_widget._messageNoValue = 'Any'

        status = None
        if self.status_widget.hasValidInput():
            status = self.status_widget.getInputValue()

        if status is not None:
            imports = self.context.search(
                review_status=status)
        else:
            imports = self.context.getAll()

        imports = sorted(imports, key=operator.attrgetter('id'))

        self.batchnav = BatchNavigator(imports, self.request, size=50)


class CodeImportView(LaunchpadView):
    def initialize(self):
        self.title = "Code Import for %s"%(self.context.product.name,)
