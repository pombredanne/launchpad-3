# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for the bug tag entry UI."""

__metaclass__ = type
__all__ = []

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser

def test_bug_tags_entry():
    """Test bug tags inline, auto-completing UI."""
    client = WindmillTestClient('Bug tags entry test')

    # First, we add some official tags to test with

    client.open(url='http://bugs.launchpad.dev:8085/firefox')
    client.waits.forPageLoad(timeout=u'20000')

    lpuser.FOO_BAR.ensure_login(client)
    client.click(link=u'Edit official tags')
    client.waits.forPageLoad(timeout=u'20000')

    client.type(text=u'eenie', id=u'new-tag-text')
    client.click(id=u'new-tag-add')
    client.type(text=u'meenie', id=u'new-tag-text')
    client.click(id=u'new-tag-add')
    client.type(text=u'meinie', id=u'new-tag-text')
    client.click(id=u'new-tag-add')
    client.type(text=u'moe', id=u'new-tag-text')
    client.click(id=u'new-tag-add')
    client.click(id=u'save-button')
    client.waits.forPageLoad(timeout=u'20000')

    client.open(url='http://bugs.launchpad.dev:8085/firefox/+bug/5')
    client.waits.forPageLoad(timeout=u'20000')
    
    client.click(id=u'edit-tags-trigger')
    client.asserts.assertNode(id=u'tag-input')
    client.type(text=u'e', id=u'tag-input')
    client.asserts.assertNode(classname=u'yui-autocomplete-list')
    client.click(id=u'item0')

