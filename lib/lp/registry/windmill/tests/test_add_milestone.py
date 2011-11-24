# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test adding milestone in formoverlay."""

__metaclass__ = type
__all__ = []

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )


class TestAddMilestone(WindmillTestCase):
    """Test form overlay widget for adding a milestone."""

    layer = RegistryWindmillLayer
    suite_name = 'AddMilestone'

    def test_adding_milestone_on_addrelease_page(self):
        """Test the form overlay for adding a milestone.

        :param name: Name of the test.
        :param url: Starting url.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        milestone_name = u'FOObar'
        code_name = u'code-%s' % milestone_name

        client, start_url = self.getClientFor(
            '/bzr/trunk/+addrelease', user=lpuser.FOO_BAR)
        client.waits.forElement(
            id=u'field.milestone_for_release', timeout=FOR_ELEMENT)

        # Click the "Create milestone" link.
        client.click(id=u'create-milestone-link')

        # Submit milestone form.
        client.waits.forElement(id=u'field.name', timeout=FOR_ELEMENT)
        client.type(id='field.name', text=milestone_name)
        client.type(id='field.code_name', text=code_name)
        client.type(id='field.dateexpected', text=u"2004-01-05")
        client.type(id='field.summary', text=u"foo bar")
        client.click(id=u'formoverlay-add-milestone')

        # Verify that the milestone was added to the SELECT input,
        # and that it is now selected.
        # XXX: push to YUI test, if we care.
        client.waits.sleep(milliseconds=SLEEP)
        client.asserts.assertSelected(id="field.milestone_for_release",
                                      validator=milestone_name.lower())

        # Verify error message when trying to create a milestone with a
        # conflicting name.
        # XXX: don't check errors in browser
        client.click(id=u'create-milestone-link')
        client.waits.forElement(id=u'field.name', timeout=FOR_ELEMENT)
        client.type(id='field.name', text=milestone_name)
        client.click(id=u'formoverlay-add-milestone')
        client.waits.forElement(
            xpath="//div[contains(@class, 'yui3-lazr-formoverlay-errors')]/ul/li")
        client.asserts.assertTextIn(
            classname='yui3-lazr-formoverlay-errors',
            validator='The name %s is already used' % milestone_name.lower())
        client.click(classname='close-button')

        # Submit product release form.
        client.select(id='field.milestone_for_release',
                      val=milestone_name.lower())
        client.type(id='field.datereleased', text=u"2004-02-22")
        client.click(id=u'field.actions.create')
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        # Verify that the release was created.
        client.waits.forElement(id="version")
        client.asserts.assertText(
            xpath="//*[@id='version']/dd", validator=milestone_name.lower())
        client.asserts.assertText(
            xpath="//*[@id='code-name']/dd", validator=code_name)
