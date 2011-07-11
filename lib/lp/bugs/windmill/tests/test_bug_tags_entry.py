# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the bug tag entry UI."""

__metaclass__ = type
__all__ = []

import transaction
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


class TestBugTagsEntry(WindmillTestCase):
    """XXX: Move to YUI test."""

    layer = BugsWindmillLayer
    suite_name = 'Bug tags entry test'

    def test_bug_tags_entry(self):
        """Test bug tags inline, auto-completing UI."""

        # First, we add some official tags to test with

        product = self.factory.makeProduct()
        removeSecurityProxy(product).official_bug_tags = [
            u'eenie', u'meenie', u'meinie', u'moe']
        bug = self.factory.makeBug(product=product)
        removeSecurityProxy(bug).tags = ['unofficial-tag']
        transaction.commit()


        # Now let's tag a bug using the auto-complete widget

        client, start_url = self.getClientFor(bug, user=lpuser.FOO_BAR)

        # XXX intellectronica 2009-05-26:
        # We (almost) consistently get an error on the following line
        # where instead of trigerring the onclick event handler we navigate
        # to the link's URL.

        client.waits.forElement(
            id=u'edit-tags-trigger', timeout=constants.FOR_ELEMENT)
        client.click(id=u'edit-tags-trigger')
        client.waits.forElement(
            id=u'tag-input', timeout=constants.FOR_ELEMENT)
        client.type(text=u'ee', id=u'tag-input')
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertNode(classname=u'yui3-autocomplete-list')
        client.click(id=u'item0')
        client.click(id=u'edit-tags-ok')
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertText(id=u'tag-list', validator=u'eenie')

        # Test that anonymous users are prompted to log in.

        client, start_url = self.getClientForAnonymous(bug)
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.click(id=u'edit-tags-trigger')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertJS(
            js=u'window.location.href.indexOf("+openid") > 0')
