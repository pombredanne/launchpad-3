# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    'CodeImportView',
    ]


from canonical.launchpad import _
from canonical.launchpad.interfaces import ICodeImportSet, NotFoundError
from canonical.launchpad.webapp import LaunchpadView, Navigation
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import LaunchpadDropdownWidget

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.schema import Choice

import operator


class CodeImportSetNavigation(Navigation):
    """Navigation from the CodeImportSet page.

    CodeImports objects live at http://code.launchpad.dev/+code-imports/$id
    and the breadcrumb links back to the code imports page.
    """

    usedfor = ICodeImportSet

    def breadcrumb(self):
        """See `Navigation.breadcrumb`."""
        return "Code Imports"

    def traverse(self, id):
        """See `Navigation.traverse`."""
        try:
            id = int(id)
        except ValueError:
            raise NotFoundError(id)
        return self.context.get(id)


class ReviewStatusDropdownWidget(LaunchpadDropdownWidget):
    """A <select> widget with a more appropriate 'no value' message.

    By default `LaunchpadDropdownWidget` displays 'no value' when the
    associated value is None or not supplied, which is not what we want on
    this page.
    """
    _messageNoValue = _('Any')


class CodeImportSetView(LaunchpadView):
    """The default view for `ICodeImportSet`.

    We present the CodeImportSet as a list of all imports.
    """

    def initialize(self):
        """See `LaunchpadView.initialize`."""
        status_field = Choice(
            __name__='status', title=_("Review Status"),
            vocabulary='CodeImportReviewStatus', required=False)
        self.status_widget = CustomWidgetFactory(ReviewStatusDropdownWidget)
        setUpWidget(self, 'status',  status_field, IInputWidget)

        status = None
        if self.status_widget.hasValidInput():
            status = self.status_widget.getInputValue()

        if status is not None:
            imports = self.context.search(review_status=status)
        else:
            imports = self.context.getAll()

        imports = sorted(imports, key=operator.attrgetter('id'))

        self.batchnav = BatchNavigator(imports, self.request)


class CodeImportView(LaunchpadView):
    """The default view for `ICodeImport`.

    We present the CodeImport as a simple page listing all the details of the
    import such as associated product and branch, who requested the import,
    and so on.
    """

    def initialize(self):
        """See `LaunchpadView.initialize`."""
        self.title = "Code Import for %s" % (self.context.product.name,)
