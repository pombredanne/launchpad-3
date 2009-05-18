# Copyright 2009 Canonical Ltd.  All rights reserved.

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_projects_plusnew_text_fields():
    """Test the text fields on step 1 of projects/+new page.

    On step 1 of the wizard, the URL field gets autofilled from the Name
    field.  Also, the URL field will not accept invalid characters.
    """
    client = WindmillTestClient('projects/+new step two dynamism')
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Perform step 1 of the project registration, using information that will
    # yield search results.
    client.open(url=u'http://launchpad.dev:8085/projects/+new')
    client.waits.forPageLoad(timeout=u'20000')

    client.type(text=u'dolphin', id='field.displayname')
    # The field is forced to lower case by a CSS text-transform, but that's
    # presentation and not testable.  However, the field /is/ autofilled from
    # the displayname field, and this we can test.
    client.asserts.assertValue(
        id=u'field.name',
        validator=u'dolphin')
    # If we type into the Name field something that contains some trailing
    # invalid characters, they don't end up in the URL field.
    client.type(text=u'dol@phin', id='field.displayname')
    client.asserts.assertValue(
        id=u'field.name',
        validator=u'dol')
    # Typing directly into the URL field prevents the autofilling.
    client.type(text=u'mongoose', id='field.name')
    client.type(text=u'dingo', id='field.displayname')
    client.asserts.assertValue(
        id=u'field.name',
        validator=u'mongoose')
    # But once we clear the URL field, autofilling is re-enabled.  Type a
    # backspace character to trigger this.
    client.type(text=u'\x08', id='field.name')
    client.type(text='hyena', id='field.displayname')
    client.asserts.assertValue(
        id=u'field.name',
        validator=u'hyena')
