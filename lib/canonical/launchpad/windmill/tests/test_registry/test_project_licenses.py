# Copyright 2009 Canonical Ltd.  All rights reserved.

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_project_licenses():
    """Test the dynamic aspects of the project license picker."""
    client = WindmillTestClient('firefox/+edit license picking')
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # The firefox project is as good as any.
    client.open(url=u'http://launchpad.dev:8085/firefox/+edit')
    client.waits.forPageLoad(timeout=u'20000')

    # The Recommended table is visible.
    client.asserts.assertProperty(
        id=u'recommended',
        validator='className|lazr-opened')
    # But the More table is not.
    client.asserts.assertProperty(
        id=u'more',
        validator='className|lazr-closed')
    # Neither is the Other choices.
    client.asserts.assertProperty(
        id=u'special',
        validator='className|lazr-closed')

    # Clicking on the link exposes the More section though.
    client.click(id='more-expand')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertProperty(
        id=u'more',
        validator='className|lazr-opened')

    # As does clicking on the Other choices section.
    client.click(id='special-expand')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertProperty(
        id=u'special',
        validator='className|lazr-opened')

    # Clicking on any opened link closes the section.
    client.click(id='recommended-expand')
    client.asserts.assertProperty(
        id=u'recommended',
        validator='className|lazr-closed')

    # The license details box starts out hidden.
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-closed')

    # But clicking on one of the Other/* licenses exposes it.
    client.click(id='field.licenses.26')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-opened')

    # Clicking on Other/Proprietary exposes the additional commercial
    # licensing details.
    client.asserts.assertProperty(
        id=u'proprietary',
        validator='className|lazr-closed')

    client.click(id='field.licenses.25')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-opened')
    client.asserts.assertProperty(
        id=u'proprietary',
        validator='className|lazr-opened')

    # Only when all Other/* items are unchecked does the details box get
    # hidden.
    client.click(id='field.licenses.26')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-opened')

    client.click(id='field.licenses.25')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-closed')
    client.asserts.assertProperty(
        id=u'proprietary',
        validator='className|lazr-closed')

    # Clicking on "I haven't specified..." unchecks everything and closes the
    # details box, but leaves the sections opened.
    client.click(id='field.licenses.25')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-opened')

    client.asserts.assertChecked(
        id=u'field.licenses.25')

    client.click(id='license_pending')
    client.asserts.assertNotChecked(
        id=u'field.licenses.25')
    
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-closed')

    # Submitting the form with items checked ensures that the next time the
    # page is visited, those sections will be open.  The Recommended section
    # is always open.

    client.click(id='field.licenses.25')
    client.type(id='field.license_info', text='Foo bar')
    client.click(id='field.licenses.3')
    client.click(id='field.actions.change')
    client.waits.forPageLoad(timeout=u'20000')

    client.open(url=u'http://launchpad.dev:8085/firefox/+edit')
    client.waits.forPageLoad(timeout=u'20000')

    client.asserts.assertProperty(
        id=u'more',
        validator='className|lazr-opened')
    # Neither is the Other choices.
    client.asserts.assertProperty(
        id=u'special',
        validator='className|lazr-opened')
    client.asserts.assertProperty(
        id=u'license-details',
        validator='className|lazr-opened')
