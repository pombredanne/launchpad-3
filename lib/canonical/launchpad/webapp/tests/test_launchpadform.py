import unittest

from zope.interface import directlyProvides
from canonical.launchpad.webapp import LaunchpadFormView
from canonical.launchpad.webapp.interfaces import (
    ISingleLineWidgetLayout, IMultiLineWidgetLayout, ICheckBoxWidgetLayout)
from canonical.testing import FunctionalLayer


class LaunchpadFormTest(unittest.TestCase):

    layer = FunctionalLayer

    def test_formLayout(self):
        # Verify that exactly one of isSingleLineLayout(), isMultiLineLayout()
        # and isCheckBoxLayout() return True for particular widget.
        #
        # If more than one returns True, then that widget may get included
        # in the form twice.
        form = LaunchpadFormView(None, None)
        class FakeWidget:
            pass
        widget = FakeWidget()
        form.widgets = {'widget': widget}
        # test every combination of the three interfaces:
        for use_single_line in [False, True]:
            for use_multi_line in [False, True]:
                for use_checkbox in [False, True]:
                    provides = []
                    if use_single_line:
                        provides.append(ISingleLineWidgetLayout)
                    if use_multi_line:
                        provides.append(IMultiLineWidgetLayout)
                    if use_checkbox:
                        provides.append(ICheckBoxWidgetLayout)
                    directlyProvides(widget, *provides)

                    # Now count how many of the is* functions return True:
                    count = 0
                    if form.isSingleLineLayout('widget'):
                        count += 1
                    if form.isMultiLineLayout('widget'):
                        count += 1
                    if form.isCheckBoxLayout('widget'):
                        count += 1

                    self.assertEqual(count, 1,
                                     'Expected count of 1 for %r.  Got %d'
                                     % (provides, count))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
