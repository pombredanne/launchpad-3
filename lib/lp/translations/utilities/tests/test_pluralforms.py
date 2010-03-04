# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from lp.translations.utilities.pluralforms import (
    BadPluralExpression,
    make_friendly_plural_forms)

class PluralFormsTest(unittest.TestCase):
    """Test utilities for handling plural forms."""

    def test_make_friendly_plural_form(self):
        single_form = make_friendly_plural_forms('0', 1)
        self.assertEqual(single_form,
                         [{'examples': [1, 2, 3, 4, 5, 6], 'form': 0}])

        two_forms = make_friendly_plural_forms('n!=1', 2)
        self.assertEqual(two_forms,
                         [{'examples': [1], 'form': 0},
                          {'examples': [2, 3, 4, 5, 6, 7], 'form': 1}])

    def test_make_friendly_plural_form_failures(self):
        # To the degree of is not accepted.
        self.assertRaises(BadPluralExpression,
                          make_friendly_plural_forms, 'n**2', 1)

        # Expressions longer than 500 characters are not accepted.
        self.assertRaises(BadPluralExpression,
                          make_friendly_plural_forms, '1'*501, 1)

        # Using arbitrary variable names is not allowed.
        self.assertRaises(BadPluralExpression,
                          make_friendly_plural_forms, '(a=1)', 1)

    def test_make_friendly_plural_form_zero_handling(self):
        zero_forms = make_friendly_plural_forms('n!=0', 2)
        self.assertEqual(zero_forms,
                         [{'examples': [0], 'form': 0},
                          {'examples': [1, 2, 3, 4, 5, 6], 'form': 1}])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PluralFormsTest))
    return suite

