# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.app.form.browser.textwidgets import IntWidget

class BugWidget(IntWidget):
    """A widget for displaying a field that is bound to an IBug."""
    def setRenderedValue(self, value):
        """Set the value to be the bug's ID."""
        display_value = None
        if value is not None:
            display_value = value.id

        IntWidget.setRenderedValue(self, display_value)
