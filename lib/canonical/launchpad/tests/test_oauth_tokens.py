# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from datetime import (
    datetime,
    timedelta
    )
import pytz

from canonical.launchpad.webapp.interfaces import OAuthPermission
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.testing import (
    TestCaseWithFactory,
    )


class TestRequestTokens(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Set up a dummy person and OAuth consumer."""
        super(TestRequestTokens, self).setUp()

        self.person = self.factory.makePerson()
        self.consumer = self.factory.makeOAuthConsumer()

        now = datetime.now(pytz.timezone('UTC'))
        self.a_long_time_ago = now - timedelta(hours=1000)

    def testExpiredRequestTokenCantBeReviewed(self):
        """An expired request token can't be reviewed."""
        token = self.factory.makeOAuthRequestToken(
            date_created=self.a_long_time_ago)
        self.assertRaises(
            AssertionError, token.review, self.person,
            OAuthPermission.WRITE_PUBLIC)

    def testExpiredRequestTokenCantBeExchanged(self):
        """An expired request token can't be exchanged for an access token.

        This can only happen if the token was reviewed before it expired.
        """
        token = self.factory.makeOAuthRequestToken(
            date_created=self.a_long_time_ago, reviewed_by=self.person)
        self.assertRaises(AssertionError, token.createAccessToken)
