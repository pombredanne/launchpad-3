# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.testing import TestCase

from canonical.buildd.check_implicit_pointer_functions import implicit_pattern
from canonical.buildd.check_implicit_pointer_functions import pointer_pattern


class TestPointerCheckRegexes(TestCase):

    def test_catches_pointer_from_integer_without_column_number(self):
        # Regex should match compiler errors that don't include the
        # column number.
        line = (
            "/build/buildd/gtk+3.0-3.0.0/./gtk/ubuntumenuproxymodule.c:94: "
            "warning: assignment makes pointer from integer without a cast")
        self.assertIsNot(None, pointer_pattern.match(line))

    def test_catches_pointer_from_integer_with_column_number(self):
        # Regex should match compiler errors that do include the
        # column number.
        line = (
            "/build/buildd/gtk+3.0-3.0.0/./gtk/ubuntumenuproxymodule.c:94:7: "
            "warning: assignment makes pointer from integer without a cast")
        self.assertIsNot(None, pointer_pattern.match(line))

    def test_catches_implicit_function_without_column_number(self):
        # Regex should match compiler errors that do include the
        # column number.
        line = (
            "/build/buildd/gtk+3.0-3.0.0/./gtk/ubuntumenuproxymodule.c:94: "
            "warning: implicit declaration of function 'foo'")
        self.assertIsNot(None, implicit_pattern.match(line))

    def test_catches_implicit_function_with_column_number(self):
        # Regex should match compiler errors that do include the
        # column number.
        line = (
            "/build/buildd/gtk+3.0-3.0.0/./gtk/ubuntumenuproxymodule.c:94:7: "
            "warning: implicit declaration of function 'foo'")
        self.assertIsNot(None, implicit_pattern.match(line))

