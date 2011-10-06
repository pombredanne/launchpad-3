# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for branch statuses."""

__metaclass__ = type
__all__ = []

import transaction

from storm.store import Store

from lp.code.enums import BranchLifecycleStatus
from lp.code.model.branch import Branch
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.constants import FOR_ELEMENT


class TestBranchStatus(WindmillTestCase):
    """Test setting branch status."""

    layer = CodeWindmillLayer
    suite_name = "Branch status setting"

    def test_inline_branch_status_setting(self):
        """Set the status of a branch."""
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        branch = self.factory.makeBranch(owner=eric)
        transaction.commit()

        client, start_url = self.getClientFor(branch, user=eric)
        # Click on the element containing the branch status.
        client.click(id=u'edit-lifecycle_status')
        client.waits.forElement(
            classname=u'yui3-ichoicelist-content', timeout=FOR_ELEMENT)
        client.click(link=u'Experimental')
        client.waits.forElement(
            jquery=u'("div#edit-lifecycle_status a.editicon.sprite.edit")',
            timeout=FOR_ELEMENT)
        client.asserts.assertTextIn(
            id=u'edit-lifecycle_status', validator=u'Experimental')
        client.asserts.assertNode(
            jquery=u'("div#edit-lifecycle_status span.value.branchstatusEXPERIMENTAL")')

        transaction.commit()
        freshly_fetched_branch = Store.of(branch).find(
            Branch, Branch.id == branch.id).one()
        self.assertEqual(
            BranchLifecycleStatus.EXPERIMENTAL,
            freshly_fetched_branch.lifecycle_status)
