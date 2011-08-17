# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for traversal from the root branch object."""

__metaclass__ = type

from zope.publisher.interfaces import NotFound

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.publication import test_traverse


class TestMacroNontraversability(TestCaseWithFactory):
    """Macros should not be URL accessable (see bug 162868)."""

    layer = DatabaseFunctionalLayer

    # Names of some macros that are tested to ensure that they're not
    # accessable via URL.  This is not an exhaustive list.
    macro_names = (
        'feed-entry-atom',
        '+base-layout-macros',
        '+main-template-macros',
        'launchpad_form',
        'launchpad_widget_macros',
        '+forbidden-page-macros',
        '+search-form',
        '+primary-search-form"',
        'form-picker-macros',
        '+filebug-macros',
        '+bugtarget-macros-search',
        'bugcomment-macros',
        'bug-attachment-macros',
        '+portlet-malone-bugmail-filtering-faq',
        '+bugtask-macros-tableview',
        'bugtask-macros-cve',
        '+bmp-macros',
        'branch-form-macros',
        '+bmq-macros',
        '+announcement-macros',
        '+person-macros',
        '+milestone-macros',
        '+distributionmirror-macros',
        '+timeline-macros',
        '+macros',
        '+rosetta-status-legend',
        '+translations-macros',
        '+object-reassignment',
    )

    def assertNotFound(self, path):
        def traverse_and_call():
            view = test_traverse(path)[1]
            view()
        self.assertRaises(NotFound, traverse_and_call)

    def test_macro_names_not_traversable(self):
        for name in self.macro_names:
            try:
                self.assertNotFound('http://launchpad.dev/' + name)
            except AssertionError, e:
                # Make any test errors more informative.
                raise AssertionError(
                    'macro name %r should not be URL accessable' % name)
