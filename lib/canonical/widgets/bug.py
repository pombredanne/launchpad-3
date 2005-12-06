# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.app.form.browser.textwidgets import IntWidget
from zope.component import getUtility
from zope.exceptions import NotFoundError
from zope.app.form.interfaces import ConversionError

from canonical.launchpad.interfaces import IBugSet

class BugWidget(IntWidget):
    """A widget for displaying a field that is bound to an IBug."""
    def setRenderedValue(self, value):
        """Set the value to be the bug's ID."""
        display_value = None
        if value is not None:
            display_value = value.id

        IntWidget.setRenderedValue(self, display_value)

    def _toFieldValue(self, input):
        if input == self._missing:
            return self.context.missing_value
        else:
            try:
                return getUtility(IBugSet).get(input)
            except (NotFoundError, ValueError):
                raise ConversionError("Not a valid bug number.")

