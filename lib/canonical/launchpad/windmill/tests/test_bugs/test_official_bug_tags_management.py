# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for the official bug tag management UI."""

__metaclass__ = type
__all__ = []

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser

def test_official_bug_tags_management():
    """Test the official bug tags management interface."""
    client = WindmillTestClient('Official bug tags management test')

    client.open(url='http://bugs.launchpad.dev:8085/firefox')
    client.waits.forPageLoad(timeout=u'20000')
    lpuser.FOO_BAR.ensure_login(client) # DEBUG
    client.click(link=u'Edit official tags')
    client.waits.forPageLoad(timeout=u'20000')
    a_new_tag = u'a-new-tag'
    client.type(text=a_new_tag, id=u'new-tag-text')
    client.click(id=u'new-tag-add')
    client.asserts.assertNode(
        xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
    client.asserts.assertText(
        xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]/label' %
               a_new_tag),
        validator=a_new_tag)
    another_new_tag = u'another-new-tag'
    client.type(text=another_new_tag, id=u'new-tag-text')
    client.keyPress(options='\\13,true,false,false,false,false', id=u'new-tag-text')
    client.asserts.assertNode(
        xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' %
               another_new_tag))
    client.asserts.assertText(
        xpath=(u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]/label' %
               another_new_tag),
        validator=another_new_tag)
    client.asserts.assertElemJS(
        id=u'remove-official-tags', js=u'element.disabled')
    client.click(id=u'tag-checkbox-%s' % a_new_tag)
    client.asserts.assertElemJS(
        id=u'remove-official-tags', js=u'!element.disabled')
    client.click(id=u'remove-official-tags')
    client.asserts.assertNode(
        xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
    client.asserts.assertNotNode(
        xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
    client.asserts.assertElemJS(
        id=u'add-official-tags', js=u'element.disabled')
    client.click(id=u'tag-checkbox-%s' % a_new_tag)
    doc_tag = u'doc'
    client.click(id=u'tag-checkbox-%s' % doc_tag)
    client.asserts.assertElemJS(
        id=u'add-official-tags', js=u'!element.disabled')
    client.click(id=u'add-official-tags')
    client.asserts.assertNode(
        xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
    client.asserts.assertNotNode(
        xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % a_new_tag)
    client.asserts.assertNode(
        xpath=u'//ul[@id="official-tags-list"]/li[@id="tag-%s"]' % doc_tag)
    client.asserts.assertNotNode(
        xpath=u'//ul[@id="other-tags-list"]/li[@id="tag-%s"]' % doc_tag)
    client.asserts.assertElemJS(
        id=u'add-official-tags', js=u'element.disabled')
    client.click(id=u'save-button')
    client.waits.forPageLoad(timeout=u'20000')
    client.click(link=u'Edit official tags')
    client.waits.forPageLoad(timeout=u'20000')

