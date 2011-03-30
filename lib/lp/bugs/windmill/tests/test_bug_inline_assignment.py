# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    SLEEP,
    )


SUBSCRIPTION_LINK = u'//div[@id="portlet-subscribers"]/div/div/a'
PERSON_LINK = u'//div[@id="subscribers-links"]/div/a[@name="%s"]'


class TestInlineAssignment(WindmillTestCase):

    layer = BugsWindmillLayer

    def test_inline_assignment_non_contributer(self):
        """Test assigning bug to a non contributer displays a notification."""

        import transaction
        # Create a person who has not contributed
        fred = self.factory.makePerson(name="fred")
        transaction.commit()

        client, start_url = self.getClientFor(
            "/firefox/+bug/1", lpuser.SAMPLE_PERSON)

        ASSIGN_BUTTON = (u'("#affected-software tr td:nth-child(5) '
            '.yui3-activator-act")')
        client.waits.forElement(jquery=ASSIGN_BUTTON, timeout=FOR_ELEMENT)
        client.click(jquery=ASSIGN_BUTTON+'[0]')

        client.type(jquery="ss", "fred")
        client.click(jquery="ss", "fred")

        client.waits.forElement(jquery="aaa", timeout=FOR_ELEMENT)
