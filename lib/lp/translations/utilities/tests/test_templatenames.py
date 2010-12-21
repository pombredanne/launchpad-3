# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from lp.translations.utilities.template import (
    make_domain,
    make_name,
    make_name_from_path,
    )


class TemplateNamesTest(unittest.TestCase):
    """Test template name conversion utility function."""

    valid_paths = [
        "my_domain.pot",
        "po/my_domain.pot",
        "my_domain/messages.pot",
        "po/my_domain/messages.pot",
        "my_domain/po/messages.pot",
        "my_domain/en-US.xpi",
        ]

    invalid_paths = [
        "messages.pot",
        "po/messages.pot",
        "en-US.xpi",
        "po/en-US.xpi",
        ]

    def test_make_domain_valid_paths(self):
        # Valid paths yield "my_domain" as the translation domain.
        for path in self.valid_paths:
            domain = make_domain(path)
            self.assertEqual('my_domain', domain,
                "Path '%s' yielded domain '%s'" % (path, domain))

    def test_make_domain_invalid_paths(self):
        # Invalid paths yield the empty string as the translation domain.
        for path in self.invalid_paths:
            domain = make_domain(path)
            self.assertEqual('', domain,
                "Path '%s' yielded domain '%s'" % (path, domain))

    def test_make_name_underscore(self):
        # Underscores are converted to dashes for template names.
        self.assertEqual('my-domain', make_name('my_domain'))

    def test_make_name_lowercase(self):
        # Upper case letters are converted to lower case for template names.
        self.assertEqual('mydomain', make_name('MyDomain'))

    def test_make_name_invalid_chars(self):
        # Invalid characters are removed for template names.
        self.assertEqual('my-domain', make_name('my - do@ #*$&main'))

    def test_make_name_from_path(self):
        # Chain both methods for convenience.
        self.assertEqual('my-domain', make_name_from_path(
            "po/My_Do@main/messages.pot"))

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

