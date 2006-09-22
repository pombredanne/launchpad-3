# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from zope.app.form.interfaces import ConversionError
from zope.app.form.browser.textwidgets import TextWidget
from canonical.launchpad.webapp.uri import Uri, InvalidUriError

#XXX matsubara 2006-05-10: Should I move our NewLineToSpacesWidget to 
# this module?


class StrippedTextWidget(TextWidget):
    """A widget that strips leading and trailing whitespaces."""

    def _toFieldValue(self, input):
        return TextWidget._toFieldValue(self, input.strip())


class UriWidget(TextWidget):
    """A widget that represents a URI."""

    displayWidth = 44
    cssClass = 'urlTextType'

    def _toFieldValue(self, input):
        if isinstance(input, list):
            raise ConversionError('Only a single value is expected')
        input = input.strip()
        if input:
            try:
                uri = Uri(input.strip())
            except InvalidUriError, e:
                raise ConversionError(str(e))
            input = str(uri)
        return TextWidget._toFieldValue(self, input)
