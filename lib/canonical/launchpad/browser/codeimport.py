# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetView',
    'CodeImportView',
    ]


from canonical.launchpad import _
from canonical.launchpad.interfaces import CodeImportReviewStatus
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import LaunchpadDropdownWidget

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.schema import Choice

import operator


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
            vocabulary=CodeImportReviewStatus, required=False)
        self.status_widget = CustomWidgetFactory(ReviewStatusDropdownWidget)
        setUpWidget(self, 'status',  status_field, IInputWidget)

        # status should be None if either (a) there were no query arguments
        # supplied, i.e. the user browsed directly to this page (this is when
        # hasValidInput returns False) or (b) the user chose 'Any' in the
        # status widget (this is when hasValidInput returns True but
        # getInputValue returns None).
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
