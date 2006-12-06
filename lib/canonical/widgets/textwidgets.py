# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from zope.app.form.interfaces import ConversionError
from zope.app.form.browser.textwidgets import TextWidget
from canonical.launchpad.webapp.uri import URI, InvalidURIError

#XXX matsubara 2006-05-10: Should I move our NewLineToSpacesWidget to 
# this module?


class StrippedTextWidget(TextWidget):
    """A widget that strips leading and trailing whitespaces."""

    def _toFieldValue(self, input):
        return TextWidget._toFieldValue(self, input.strip())


class URIWidget(TextWidget):
    """A widget that represents a URI."""

    displayWidth = 44
    cssClass = 'urlTextType'

    def _toFieldValue(self, input):
        """Convert the form input value to a field value.

        This method differs from the standard TextWidget behaviour in
        the following ways:
         * whitespace is stripped from the input value
         * invalid URIs cause a ConversionError
         * if the field requires (or forbids) a trailing slash on the URI,
           then the widget ensures that the widget ends in a slash (or
           doesn't end in a slash).
         * the URI is canonicalised.

        Extra validation is left to the field implementation.

          >>> from zope.publisher.browser import TestRequest
          >>> from canonical.launchpad.fields import URIField
          >>> field = URIField(__name__='foo', title=u'Foo')
          >>> widget = URIWidget(field, TestRequest())

        Whitespace is stripped from the value:
          >>> widget._toFieldValue('  http://www.ubuntu.com/   ')
          u'http://www.ubuntu.com/'

        Invalid URIs cause a ConversionError:
          >>> widget._toFieldValue('not-a-uri')
          Traceback (most recent call last):
            ...
          ConversionError: ('"not-a-uri" is not a valid URI', None)

        Trailing slashes are added or removed if necessary:
          >>> field.trailing_slash = True
          >>> widget._toFieldValue('http://www.ubuntu.com/ubuntu?action=raw')
          u'http://www.ubuntu.com/ubuntu/?action=raw'

          >>> field.trailing_slash = False
          >>> widget._toFieldValue('http://www.ubuntu.com/ubuntu/?action=edit')
          u'http://www.ubuntu.com/ubuntu?action=edit'
          >>> field.trailing_slash = None

        URIs are canonicalised:
          >>> widget._toFieldValue('HTTP://People.Ubuntu.COM:80/%7Ejamesh/')
          u'http://people.ubuntu.com/~jamesh/'
        """
        if isinstance(input, list):
            raise ConversionError('Only a single value is expected')
        input = input.strip()
        if input:
            try:
                uri = URI(input.strip())
            except InvalidURIError, e:
                raise ConversionError(str(e))
            # If there is a policy 
            if self.context.trailing_slash is not None:
                if self.context.trailing_slash:
                    uri = uri.ensureSlash()
                else:
                    uri = uri.ensureNoSlash()
            input = str(uri)
        return TextWidget._toFieldValue(self, input)
