# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lp.translations.utilities.validate import validate_translations


class TestTranslationValidation(unittest.TestCase):
    """Test how translation validation works."""

    def test_validate_translations_c_format(self):
        # Correct c-format translations will be validated.
        english = ["English %s number %d"]
        flags = ["c-format"]
        translations = ["Translation %s number %d"]
        self.assertTrue(
            validate_translations(english, translations, flags))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
