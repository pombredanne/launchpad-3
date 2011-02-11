# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for form for creating a project."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


class TestNewProjectStep2(WindmillTestCase):
    """Test form for creating a new project."""

    layer = RegistryWindmillLayer
    suite_name = 'TestNewProjectStep2'

    def test_projects_plusnew_step_two(self):
        """Test the dynamic aspects of step 2 of projects/+new page.

        When the project being registered matches existing projects, the
        step two page has some extra javascript-y goodness.  At the
        start, there's a 'No' button that hides the search results and
        reveals the rest of the project registration form.  After that,
        there's a href that toggles between revealing the search results
        and hiding them.
        """

        # Perform step 1 of the project registration, using information
        # that will yield search results.
        self.client.open(url=u'%s/projects/+new'
                        % RegistryWindmillLayer.base_url)

        lpuser.SAMPLE_PERSON.ensure_login(self.client)

        self.client.waits.forElement(id='field.displayname', timeout=u'20000')
        self.client.type(text=u'Badgers', id='field.displayname')
        self.client.type(text=u'badgers', id='field.name')
        self.client.type(text=u"There's the Badger", id='field.title')
        self.client.type(text=u'Badgers ate my firefox', id='field.summary')
        self.client.click(id=u'field.actions.continue')
        self.client.waits.forPageLoad(timeout=u'20000')
        # The h2 heading indicates that a search was performed.
        self.client.asserts.assertTextIn(
            id=u'step-title',
            validator=u'Check for duplicate projects')

        # Clicking on the "No" button hides the button and search
        # results, reveals the form widgets, and reveals an href link
        # for toggling the search results.  It also changes the h2 title
        # to something more appropriate.
        self.client.click(id=u'registration-details-buttons')
        self.client.asserts.assertTextIn(
            id=u'step-title',
            validator=u'Registration details')

        # The className for hidden elements is lazr-closed  because it's
        # set by the slide-in effect.  For slide-out elements, it's
        # lazr-opened.
        self.client.asserts.assertProperty(
            id='search-results', validator='className|lazr-closed')
        self.client.asserts.assertProperty(
            id=u'launchpad-form-widgets',
            validator='className|lazr-opened')
        self.client.asserts.assertNotProperty(
            id=u'search-results-expander',
            validator='className|unseen')
        # Clicking on the href expands the search results.
        self.client.click(id='search-results-expander')
        self.client.waits.forElement(
            xpath='//*[@id="search-results" '
                  'and contains(@class, "lazr-opened")]',
            milliseconds=u'1000')
        self.client.asserts.assertProperty(
            id=u'search-results',
            validator='className|lazr-opened')
        # Clicking it again hides the results.
        self.client.click(id='search-results-expander')
        self.client.waits.forElement(
            xpath='//*[@id="search-results" '
                  'and contains(@class, "lazr-closed")]',
            milliseconds=u'1000')
        self.client.asserts.assertProperty(
            id=u'search-results',
            validator='className|lazr-closed')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
