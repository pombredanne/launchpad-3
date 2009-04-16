# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for translation import queue behaviour."""

__metaclass__ = type
__all__ = []

import time

from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient


class InlineAddMilestoneForReleaseTest:
    """Test adding a milestone inline."""

    def __init__(self, name=None,
                 url='http://launchpad.dev:8085/bzr/trunk/+addrelease',
                 suite='milestone', user=lpuser.FOO_BAR):
        """Create a new InlineAddMilestoneForReleaseTest.

        :param name: Name of the test.
        :param url: Starting url.
        :param suite: The suite in which this test is part of.
        :param user: The user who should be logged in.
        """
        self.url = url
        if name is None:
            self.__name__ = 'test_%s_add_milestone' % suite
        else:
            self.__name__ = name
        self.suite = suite
        self.user = user
        self.client = None

    def __call__(self):
        """Tests creating new milestone for a release."""
        # Ensure that the milestone name doesn't conflict with previous
        # test runs.
        milestone_name = u'%x' % int(time.time())
        code_name = u'code-%s' % milestone_name

        self.client = WindmillTestClient(self.suite)

        self.user.ensure_login(self.client)
        self.client.open(url=self.url)
        self.client.waits.forPageLoad(timeout=u'20000')

        self.client.waits.forElement(id=u'field.milestone_for_release',
                                     timeout=u'8000')

        # Select "Create milestone..." from the milestone SELECT menu.
        self.client.select(id='field.milestone_for_release',
                           option='Create milestone...')

        # Submit milestone form.
        self.client.waits.forElement(id=u'field.name', timeout=u'8000')
        self.client.type(id='field.name', text=milestone_name)
        self.client.type(id='field.code_name', text=code_name)
        self.client.type(id='field.dateexpected', text=u"2004-01-05")
        self.client.type(id='field.summary', text=u"foo bar")
        self.client.click(id=u'formoverlay-add-milestone')

        # Verify that the milestone was added to the SELECT input,
        # and that it is now selected.
        self.client.waits.sleep(milliseconds='1000')
        self.client.asserts.assertSelected(id="field.milestone_for_release",
                                           validator=milestone_name)

        # Verify error message when trying to create a milestone with a
        # conflicting name.
        self.client.select(id='field.milestone_for_release',
                           option='Create milestone...')
        self.client.waits.forElement(id=u'field.name', timeout=u'8000')
        self.client.type(id='field.name', text=milestone_name)
        self.client.click(id=u'formoverlay-add-milestone')
        self.client.asserts.assertText(
            id='milestone-error',
            validator='The name %s is already used' % milestone_name)
        self.client.click(classname='close-button')

        # Submit product release form.
        self.client.select(id='field.milestone_for_release', val=milestone_name)
        self.client.type(id='field.datereleased', text=u"2004-02-22")
        self.client.click(id=u'field.actions.create')
        self.client.waits.forPageLoad(timeout=u'20000')

        # Verify that the release was created.
        self.client.waits.forElement(
            xpath="//table[@id='series_trunk']"
                  "//a[@href='/bzr/trunk/%s']" % milestone_name,
            timeout=u'8000')
        self.client.asserts.assertText(
            xpath="//table[@id='series_trunk']"
                  "//a[@href='/bzr/trunk/%s']" % milestone_name,
            validator=milestone_name)
        self.client.asserts.assertText(
            xpath="//table[@id='series_trunk']"
                  "//a[@href='/bzr/trunk/%s']"
                  "/ancestor::td/following-sibling::td" % milestone_name,
            validator=code_name)


test_inline_add_milestone_for_release = InlineAddMilestoneForReleaseTest(
    name='test_inline_add_milestone_for_release')
