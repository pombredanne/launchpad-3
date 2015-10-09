# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import (
    Equals,
    Is,
    MatchesDict,
    )

from lp.registry.interfaces.product import IProduct
from lp.services.webhooks.payload import compose_webhook_payload
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestComposeWebhookPayload(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_serialises(self):
        project = self.factory.makeProduct()
        self.assertThat(
            compose_webhook_payload(
                IProduct, project, ["display_name", "owner", "projectgroup"]),
            MatchesDict({
                "display_name": Equals(project.display_name),
                "owner": Equals("/~%s" % project.owner.name),
                "projectgroup": Is(None),
                }))
