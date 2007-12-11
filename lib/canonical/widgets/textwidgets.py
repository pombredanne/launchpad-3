# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

import datetime
import pytz

from zope.app.datetimeutils import parse, DateTimeError
from zope.app.form.browser.textwidgets import TextAreaWidget, TextWidget
from zope.app.form.interfaces import ConversionError

from canonical.launchpad.interfaces import UnexpectedFormData
from canonical.launchpad.webapp.uri import URI, InvalidURIError

# XXX matsubara 2006-05-10: Should I move our NewLineToSpacesWidget to
# this module?


class StrippedTextWidget(TextWidget):
    """A widget that strips leading and trailing whitespaces."""

    def _toFieldValue(self, input):
        return TextWidget._toFieldValue(self, input.strip())


class LowerCaseTextWidget(StrippedTextWidget):
    """A widget that converts text to lower case."""

    cssClass = 'lowerCaseText'

    def _toFieldValue(self, input):
        return StrippedTextWidget._toFieldValue(self, input.lower())


class LocalDateTimeWidget(TextWidget):
    """A datetime widget that uses a particular time zone."""

    timeZoneName = 'UTC'

    def _toFieldValue(self, input):
        """Convert a string to a datetime value.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = LocalDateTimeWidget(field, TestRequest())

        The widget converts an empty string to the missing value:

          >>> widget._toFieldValue('') == field.missing_value
          True

        By default, the date is interpreted as UTC:

          >>> print widget._toFieldValue('2006-01-01 12:00:00')
          2006-01-01 12:00:00+00:00

        But it will handle other time zones:

          >>> widget.timeZoneName = 'Australia/Perth'
          >>> print widget._toFieldValue('2006-01-01 12:00:00')
          2006-01-01 12:00:00+08:00

        Invalid dates result in a ConversionError:

          >>> print widget._toFieldValue('not a date')  #doctest: +ELLIPSIS
          Traceback (most recent call last):
            ...
          ConversionError: ('Invalid date value', ...)
        """
        if input == self._missing:
            return self.context.missing_value
        try:
            year, month, day, hour, minute, second, dummy_tz = parse(input)
            second, micro = divmod(second, 1.0)
            micro = round(micro * 1000000)
            dt = datetime.datetime(year, month, day,
                                   hour, minute, int(second), int(micro))
        except (DateTimeError, ValueError, IndexError), v:
            raise ConversionError('Invalid date value', v)
        tz = pytz.timezone(self.timeZoneName)
        return tz.localize(dt)

    def _toFormValue(self, value):
        """Convert a date to its string representation.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = LocalDateTimeWidget(field, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        Dates are displayed without an associated time zone:

          >>> dt = datetime.datetime(2006, 1, 1, 12, 0, 0,
          ...                        tzinfo=pytz.timezone('UTC'))
          >>> widget._toFormValue(dt)
          '2006-01-01 12:00:00'

        The date value will be converted to the widget's time zone
        before being displayed:

          >>> widget.timeZoneName = 'Australia/Perth'
          >>> widget._toFormValue(dt)
          '2006-01-01 20:00:00'
        """
        if value == self.context.missing_value:
            return self._missing
        tz = pytz.timezone(self.timeZoneName)
        return value.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')


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
        """
        if isinstance(input, list):
            raise UnexpectedFormData('Only a single value is expected')
        input = input.strip()
        if input:
            try:
                uri = URI(input)
            except InvalidURIError, exc:
                raise ConversionError(str(exc))
            # If there is a policy for whether trailing slashes are
            # allowed at the end of the path segment, ensure that the
            # URI conforms.
            if self.context.trailing_slash is not None:
                if self.context.trailing_slash:
                    uri = uri.ensureSlash()
                else:
                    uri = uri.ensureNoSlash()
            input = str(uri)
        return TextWidget._toFieldValue(self, input)


class DelimitedListWidget(TextAreaWidget):
    """A widget that represents a list as whitespace-delimited text."""

    def __init__(self, field, value_type, request):
        # We don't use value_type.
        super(DelimitedListWidget, self).__init__(field, request)

    # The default splitting function.
    split = staticmethod(unicode.split)

    # The default joining function.
    join = staticmethod(u'\n'.join)

    def _toFormValue(self, value):
        """Converts a list to a newline separated string.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DelimitedListWidget(field, None, TestRequest())

        The 'missing' value is converted to an empty string:

          >>> widget._toFormValue(field.missing_value)
          u''

        By default, lists are displayed one item on a line:

          >>> names = ['fred', 'bob', 'harry']
          >>> widget._toFormValue(names)
          u'fred\\r\\nbob\\r\\nharry'
        """
        if value == self.context.missing_value:
            value = u''
        elif value is None:
            value = u''
        else:
            value = self.join(value)
        return super(DelimitedListWidget, self)._toFormValue(value)

    def _toFieldValue(self, value):
        """Convert the input string into a list.

          >>> from zope.publisher.browser import TestRequest
          >>> from zope.schema import Field
          >>> field = Field(__name__='foo', title=u'Foo')
          >>> widget = DelimitedListWidget(field, None, TestRequest())

        The widget converts an empty string to the missing value:

          >>> widget._toFieldValue('') == field.missing_value
          True

        By default, lists are split by whitespace:

          >>> print widget._toFieldValue(u'fred\\nbob harry')
          [u'fred', u'bob', u'harry']
        """
        value = super(
            DelimitedListWidget, self)._toFieldValue(value)
        if value:
            return self.split(value)
        else:
            return self.context.missing_value
