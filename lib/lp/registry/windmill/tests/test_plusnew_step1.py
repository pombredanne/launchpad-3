# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test form for creating a new project."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


BACKSPACE = u'\x08'


class TestNewProjectStep1(WindmillTestCase):
    """Test form for creating a new project."""

    layer = RegistryWindmillLayer
    suite_name = 'TestNewProjectStep1'

    def test_projects_plusnew_text_fields(self):
        """Test the text fields on step 1 of projects/+new page.

        On step 1 of the wizard, the URL field gets autofilled from the Name
        field.  Also, the URL field will not accept invalid characters.
        """
        # Perform step 1 of the project registration, using information
        # that will yield search results.
        self.client.open(url=u'%s/projects/+new'
                        % RegistryWindmillLayer.base_url)

        lpuser.SAMPLE_PERSON.ensure_login(self.client)

        self.client.waits.forElement(id='field.displayname')
        self.client.type(text=u'dolphin', id='field.displayname')

        # The field is forced to lower case by a CSS text-transform, but
        # that's presentation and not testable.  However, the field /is/
        # autofilled from the displayname field, and this we can test.
        self.client.asserts.assertValue(
            id=u'field.name',
            validator=u'dolphin')
        # If we type into the Name field something that contains some trailing
        # invalid characters, they don't end up in the URL field.
        self.client.type(text=u'dol@phin', id='field.displayname')
        self.client.asserts.assertValue(
            id=u'field.name',
            validator=u'dol')
        # Typing directly into the URL field prevents the autofilling.
        self.client.type(text=u'mongoose', id='field.name')
        self.client.type(text=u'dingo', id='field.displayname')
        self.client.asserts.assertValue(
            id=u'field.name',
            validator=u'mongoose')
        # But once we clear the URL field, autofilling is re-enabled.  Type a
        # backspace character to trigger this.
        self.client.type(text=BACKSPACE, id='field.name')
        self.client.type(text='hyena', id='field.displayname')
        self.client.asserts.assertValue(
            id=u'field.name',
            validator=u'hyena')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
