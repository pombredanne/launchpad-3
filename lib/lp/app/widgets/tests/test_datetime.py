from datetime import datetime

from zope.app.form.interfaces import ConversionError
from zope.schema import Field

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.date import DateTimeWidget
from lp.testing import TestCase


class TestDateTimeWidget(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDateTimeWidget, self).setUp()
        field = Field(__name__='foo', title=u'Foo')
        request = LaunchpadTestRequest()
        self.widget = DateTimeWidget(field, request)

    def test_unsupported_format_errors(self):
        # Dates in unsupported formats result in a ConversionError
        self.assertRaises(
            ConversionError,
            self.widget._checkSupportedFormat,
            '15-5-2010')

    def test_unconverted_message(self):
        # The widget format checker relies on a particular mesage
        # being returned. If that breaks, this will tell us.
        test_str = "2010-01-01 10:10:10"
        fmt = "%Y-%m-%d"
        try:
            datetime.strptime(test_str, fmt)
        except (ValueError,), e:
            self.assertTrue('unconverted data' in str(e))

    def test_whitespace_does_not_trick_validation(self):
        # Trailing whitespace doesn't get through because of the
        # unconverted data issue.
        self.assertRaises(
            ConversionError,
            self.widget._checkSupportedFormat,
            '15-5-2010 ')
