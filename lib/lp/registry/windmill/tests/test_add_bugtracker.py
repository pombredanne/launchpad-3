# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test adding bug tracker in formoverlay."""

__metaclass__ = type
__all__ = []

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


class TestAddBugTracker(WindmillTestCase):
    """Test form overlay widget for adding a bug tracker."""

    # This test doesn't run well in the BugsWindmillLayer, since
    # submitting the +configure-bugtracker form takes you back to
    # the project index page, which is not on the bugs.launchpad.dev.
    layer = RegistryWindmillLayer
    suite_name = 'AddBugTracker'

    def test_adding_bugtracker_for_project(self):
        """Test the form overlay for adding a bugtracker.

        :param name: Name of the test.
        :param url: Starting url.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        bugtracker_name = u'FOObar'
        title = u'\xdf-title-%s' % bugtracker_name
        location = u'http://example.com/%s' % bugtracker_name

        client, start_url = self.getClientFor(
            '/bzr/+configure-bugtracker', user=lpuser.FOO_BAR)
        client.waits.forElement(id=u'create-bugtracker-link')

        # Click the "Create external bug tracker" link.
        client.click(id=u'create-bugtracker-link')

        # Submit bugtracker form.
        client.waits.forElement(id=u'field.name')
        client.type(id='field.name', text=bugtracker_name)
        client.type(id='field.title', text=title)
        client.type(id='field.baseurl', text=location)
        client.click(id=u'formoverlay-add-bugtracker')

        # Verify that the bugtracker name was entered in the text box.
        # XXX: pushed down to YUI tests, if we care.
        client.waits.sleep(milliseconds='1000')
        client.asserts.assertProperty(
            id="field.bugtracker.bugtracker",
            validator='value|%s' % bugtracker_name.lower())
        client.asserts.assertChecked(id="field.bugtracker.2")

        # Verify error message when trying to create a bugtracker with a
        # conflicting name.
        # XXX: no error checking in browser tests.
        client.click(id=u'create-bugtracker-link')
        client.waits.forElement(id=u'field.name')
        client.type(id='field.name', text=bugtracker_name)
        client.click(id=u'formoverlay-add-bugtracker')
        client.waits.forElement(
            xpath="//div[contains(@class, 'yui3-lazr-formoverlay-errors')]/ul/li")
        client.asserts.assertTextIn(
            classname='yui3-lazr-formoverlay-errors',
            validator='name: %s is already in use' % bugtracker_name.lower())
        client.click(classname='close-button')

        # Configure bug tracker for the project.
        client.click(id=u'field.actions.change')

        # You should now be on the project index page.
        client.waits.forElement(
            xpath="//a[contains(@class, 'menu-link-configure_bugtracker')]")
        client.click(
            xpath="//a[contains(@class, 'menu-link-configure_bugtracker')]")

        # Verify that the new bug tracker was configured for this project.
        client.waits.forElement(id="field.bugtracker.bugtracker")
        client.asserts.assertProperty(
            id="field.bugtracker.bugtracker",
            validator='value|%s' % bugtracker_name.lower())
        client.asserts.assertChecked(id="field.bugtracker.2")
