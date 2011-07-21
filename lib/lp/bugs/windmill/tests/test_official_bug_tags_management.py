# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the official bug tag management UI."""

__metaclass__ = type
__all__ = []

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


class TestOfficialBugTags(WindmillTestCase):
    """XXX: Pull most to YUI test, but port XHR check at end."""

    layer = BugsWindmillLayer
    suite_name = 'Official bug tags management test'

    def test_official_bug_tags_management(self):
        """Test the official bug tags management interface."""
        client = self.client

    # Firefox is a product - an official bug tags target.

        client, start_url = self.getClientFor('/firefox', user=lpuser.FOO_BAR)

    # foobar has the permission to edit the official bug tags for firefox.

        client.waits.forElement(
            link=u'Edit official tags', timeout=constants.FOR_ELEMENT)
        client.click(link=u'Edit official tags')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

    # There are no official tags defined (the rest of the test
    # depends on that).

        client.asserts.assertElemJS(
            id=u'official-tags-list',
            js=u'element.childNodes.length == 0',
            timeout=constants.FOR_ELEMENT)

    # The save button is disabled initially, since there's nothing to change.

        client.asserts.assertElemJS(id=u'save-button', js=u'element.disabled')

    # We type a new tag and click 'Add'.

        a_new_tag = u'a-new-tag'
        client.type(text=a_new_tag, id=u'new-tag-text')
        client.click(id=u'new-tag-add')

    # The new tag is added to the official tags list.

        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  a_new_tag)
        client.asserts.assertText(
            xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]/label' %
                   a_new_tag),
            validator=a_new_tag)

    # The save button is now enabled.

        client.asserts.assertElemJS(
            id=u'save-button', js=u'!element.disabled')

    # We type another tag, and hit [enter].

        another_new_tag = u'another-new-tag'
        client.type(text=another_new_tag + '?!', id=u'new-tag-text')
        client.keyPress(
            options='\\13,true,false,false,false,false',
            id=u'new-tag-text')

    # The tag is invalid, so we get an error message in an overlay.

        client.asserts.assertNode(id=u'yui3-pretty-overlay-modal')

    # We click the close button to dismiss the error message, type a correct
    # tag and try again.

        client.click(xpath=u'//a[@class="close-button"]')
        client.type(text=another_new_tag, id=u'new-tag-text')
        client.keyPress(
            options='\\13,true,false,false,false,false',
            id=u'new-tag-text')

    # The tag is added to the list too.

        client.asserts.assertNode(
            xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                   another_new_tag))
        client.asserts.assertText(
            xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]/label' %
                   another_new_tag),
            validator=another_new_tag)

    # Tags with dots in them are OK, but the IDs of the elements representing
    # them gets mangled.

        tag_with_dot = 'tag-with.dot'
        client.type(text=tag_with_dot, id=u'new-tag-text')
        client.keyPress(
            options='\\13,true,false,false,false,false',
            id=u'new-tag-text')

    # The tag is added to the list too.

        client.asserts.assertNode(
            xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                   tag_with_dot.replace('.', '__46__')))
        client.asserts.assertText(
            xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]/label' %
                   tag_with_dot.replace('.', '__46__')),
            validator=tag_with_dot)

    # The arrow button for moving tags out of the official tags list is
    # disabled, because no tags are selected.

        client.asserts.assertElemJS(
            id=u'remove-official-tags', js=u'element.disabled')

    # We select one tag, and the button becomes enabled.

        client.click(id=u'tag-checkbox-%s' % a_new_tag)
        client.asserts.assertElemJS(
            id=u'remove-official-tags', js=u'!element.disabled')

    # We click the button and the tag moves from the official tags list to the
    # unofficial list.

        client.click(id=u'remove-official-tags')
        client.asserts.assertNode(
            xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
        client.asserts.assertNotNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  a_new_tag)

    # The arrow button for moving tags from the unofficial to the official
    # tags list is disabled, because no unofficial tags are selected.

        client.asserts.assertElemJS(
            id=u'add-official-tags', js=u'element.disabled')

    # We select two unofficial tags and click the button. The tags move to the
    # official tags list.

        client.click(id=u'tag-checkbox-%s' % a_new_tag)
        doc_tag = u'doc'
        client.click(id=u'tag-checkbox-%s' % doc_tag)
        client.asserts.assertElemJS(
            id=u'add-official-tags', js=u'!element.disabled')
        client.click(id=u'add-official-tags')
        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  a_new_tag)
        client.asserts.assertNotNode(
            xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  doc_tag)
        client.asserts.assertNotNode(
            xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % doc_tag)

    # After moving the tags the button is disabled again, as no tags
    # are selected.

        client.asserts.assertElemJS(
            id=u'add-official-tags', js=u'element.disabled')

    # The tags are sorted alphabetically.

        client.asserts.assertElemJS(
            id=u'official-tags-list',
            js=(u"(new RegExp('.*a-new-tag.*another-new-tag.*doc'))"
                u".test(element.innerHTML)"))

    # We click 'Save' and the tags are submitted to the server. We end up back
    # on the bugs index page.

        client.click(id=u'save-button')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

    # When we go back to the tags management page we can see that our tags are
    # still there.

        client.click(link=u'Edit official tags')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
            a_new_tag,
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  another_new_tag,
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertNode(
            xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
                  doc_tag,
            timeout=constants.FOR_ELEMENT)

    # We finish by cleaning after ourselves, to make sure that we leave the
    # database at the same state we found it.

        for tag in [a_new_tag, another_new_tag, doc_tag]:
            client.click(id=u'tag-checkbox-%s' % tag)
        client.click(id=u'remove-official-tags')
        client.click(id=u'save-button')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
