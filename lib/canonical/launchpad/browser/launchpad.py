# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser code for the launchpad application."""

__metaclass__ = type
__all__ = ['LoginStatus']

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadRoot, IRosettaApplication)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, DefaultLink, Link)


class LaunchpadRootFacets(StandardLaunchpadFacets):
    usedfor = ILaunchpadRoot
    links = ['overview', 'bugs', 'translations', 'calendar']

    def overview(self):
        target = ''
        text = 'Overview'
        return DefaultLink(target, text)

    def translations(self):
        target = 'rosetta'
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = 'malone'
        text = 'Bugs'
        return Link(target, text)

    def calendar(self):
        target = 'calendar'
        text = 'Calendar'
        # merged calendar is only available when logged in
        linked = getUtility(ILaunchBag).user is not None
        return Link(target, text, linked=linked)


class RosettaAppMenus(ApplicationMenu):
    usedfor = IRosettaApplication
    facet = 'translations'
    links = ['overview', 'about']

    def overview(self):
        target = ''
        text = 'Translations'
        return DefaultLink(target, text)

    def upload(self):
        target = ''
        text = 'Upload'
        return Link(target, text)

    def download(self):
        target = ''
        text = 'Download'
        return Link(target, text)

    def about(self):
        target = '+about'
        text = 'About Rosetta'
        return Link(target, text)


class LoginStatus:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    @property
    def login_shown(self):
        return (self.user is None and
                '+login' not in self.request['PATH_INFO'])

    @property
    def logged_in(self):
        return self.user is not None

    @property
    def login_url(self):
        query_string = self.request.get('QUERY_STRING', '')
        if query_string:
            query_string = '?' + query_string

        # The approach we're taking is to combine the application url with
        # the path_info, taking out path steps that are to do with virtual
        # hosting.  This is not exactly correct, as the application url
        # can have other path steps in it.  We're not using the feature of
        # having other path steps in the application url, so this will work
        # for us, assuming we don't need that in the future.

        # The application_url is typically like 'http://thing:port'. No
        # trailing slash.
        application_url = self.request.getApplicationURL()

        # We're going to use PATH_INFO to remove any spurious '+index' at the
        # end of the URL.  But, PATH_INFO will contain virtual hosting
        # configuration, if there is any.
        path_info = self.request['PATH_INFO']

        # Remove any virtual hosting segments.
        path_steps = []
        in_virtual_hosting_section = False
        for step in path_info.split('/'):
            if step.startswith('++vh++'):
                in_virtual_hosting_section = True
                continue
            if step == '++':
                in_virtual_hosting_section = False
                continue
            if not in_virtual_hosting_section:
                path_steps.append(step)
        path = '/'.join(path_steps)

        # Make the URL stop at the end of path_info so that we don't get
        # spurious '+index' at the end.
        full_url = '%s%s' % (application_url, path)
        if full_url.endswith('/'):
            full_url = full_url[:-1]
        logout_url_end = '/+logout'
        if full_url.endswith(logout_url_end):
            full_url = full_url[:-len(logout_url_end)]
        return '%s/+login%s' % (full_url, query_string)

