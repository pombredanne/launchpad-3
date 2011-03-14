# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the CSS TALES formatter."""

__metaclass__ = type

from testtools.matchers import Equals

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    test_tales,
    TestCase,
    )


class TestCSSFormatter(TestCase):

    layer = DatabaseFunctionalLayer

    def test_select(self):
        value = test_tales('value/css:select/visible/unseen', value=None)
        self.assertThat(value, Equals('unseen'))
        value = test_tales('value/css:select/visible/unseen', value=False)
        self.assertThat(value, Equals('unseen'))
        value = test_tales('value/css:select/visible/unseen', value='')
        self.assertThat(value, Equals('unseen'))
        value = test_tales('value/css:select/visible/unseen', value=True)
        self.assertThat(value, Equals('visible'))
        value = test_tales('value/css:select/visible/unseen', value='Hello')
        self.assertThat(value, Equals('visible'))
        value = test_tales('value/css:select/visible/unseen', value=object())
        self.assertThat(value, Equals('visible'))

    def test_select_chaining(self):
        value = test_tales(
            'value/css:select/VISIBLE/UNSEEN/fmt:lower', value=None)
        self.assertThat(value, Equals('unseen'))
