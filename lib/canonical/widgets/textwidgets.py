# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from zope.app.form.browser.textwidgets import TextWidget
#XXX matsubara 2006-05-10: Should I move our NewLineToSpacesWidget to 
# this module?


class StrippedTextWidget(TextWidget):
    """A widget that strips leading and trailing whitespaces."""

    def _toFieldValue(self, input):
        return TextWidget._toFieldValue(self, input.strip())
