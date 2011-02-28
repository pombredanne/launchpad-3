# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing the Blueprint email handler."""

__metaclass__ = type

from testtools.matchers import Equals, Is

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.blueprints.mail.handler import get_spec_url_from_moin_mail
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.testing import (
    login,
    login_person,
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )


class TestGetSpecUrlFromMoinMail(TestCase):
    """Tests for get_spec_url_from_moin_mail."""

    def test_invalid_params(self):
        # Only strings and unicode are OK.
        self.assertThat(get_spec_url_from_moin_mail(None), Is(None))
        self.assertThat(get_spec_url_from_moin_mail(42), Is(None))
        self.assertThat(get_spec_url_from_moin_mail(object()), Is(None))

    def test_missing_urls(self):
        # Strings with missing URLs also return None
        self.assertThat(
            get_spec_url_from_moin_mail('nothing here'),
            Is(None))

    def test_string_contains_url(self):
        body = """
            Testing a big string

            An url, http://example.com/foo in a string
            """
        self.assertThat(
            get_spec_url_from_moin_mail(body),
            Equals('http://example.com/foo'))

    def test_two_urls(self):
        # Given two urls, only the first is returned.
        body = """
            Testing two urls:
            http://example.com/first
            http://example.com/second
            """
        self.assertThat(
            get_spec_url_from_moin_mail(body),
            Equals('http://example.com/first'))

    def test_unicode(self):
        # Given two urls, only the first is returned.
        body = u"""
            Testing unicode:
            http://example.com/\N{SNOWMAN}
            """
        self.assertThat(
            get_spec_url_from_moin_mail(body),
            Equals(u'http://example.com/\N{SNOWMAN}'))


class TestBlueprintEmailHandler(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    
