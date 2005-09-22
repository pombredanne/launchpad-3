# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser code for the launchpad application."""

__metaclass__ = type
__all__ = ['LoginStatus', 'MaintenanceMessage']

import cgi
import urllib
import os.path
from datetime import timedelta, datetime

from zope.app.datetimeutils import parseDatetimetz, tzinfo, DateTimeError
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadRoot, IRosettaApplication, IAging)
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ApplicationMenu, Link)
# XXX SteveAlexander, 2005-09-22, this is imported here because there is no
#     general timedelta to duration format adapter available.  This should
#     be factored out into a generally available adapter for both this
#     code and for TALES namespace code to use.
from canonical.launchpad.webapp.tales import DurationFormatterAPI


class MaintenanceMessage:
    """Display a maintenance message if the control file is present and
    it contains a valid iso format time.

    The maintenance message shows the approximate time before launchpad will
    be taken offline for maintenance.

    The control file is +maintenancetime.txt in the launchpad root.

    If there is no maintenance message, an empty string is returned.

    If the maintenance time is too far in the future, then an empty string
    is returned.

    If the maintenance time is in the past, then the maintenance message says
    that Launchpad will go offline "very very soon".

    If the text in the maintenance message is poorly formatted, then an
    empty string is returned, and a warning should be logged.
    """

    timelefttext = None

    notmuchtime = timedelta(seconds=30)
    toomuchtime = timedelta(seconds=1800)  # 30 minutes

    def __call__(self):
        if os.path.exists('+maintenancetime.txt'):
            message = file('+maintenancetime.txt').read()
            try:
                maintenancetime = parseDatetimetz(message)
            except DateTimeError:
                # XXX log a warning here.
                #     SteveAlexander, 2005-09-22
                return ''
            nowtz = datetime.utcnow().replace(tzinfo=tzinfo(0))
            timeleft = maintenancetime - nowtz
            if timeleft > self.toomuchtime:
                return ''
            elif timeleft < self.notmuchtime:
                self.timelefttext = 'very very soon'
            else:
                self.timelefttext = 'in %s' % (
                    DurationFormatterAPI(timeleft).approximateduration())
            return self.index()
        return ''


class LaunchpadRootFacets(StandardLaunchpadFacets):
    usedfor = ILaunchpadRoot

    def overview(self):
        target = ''
        text = 'Overview'
        return Link(target, text)

    def translations(self):
        target = 'rosetta'
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = 'malone'
        text = 'Bugs'
        return Link(target, text)

    def support(self):
        target = 'support'
        text = 'Support'
        summary = 'Launchpad technical support tracker.'
        return Link(target, text, summary)

    def specifications(self):
        target = 'specs'
        text = 'Specifications'
        summary = 'Launchpad feature specification tracker.'
        return Link(target, text, summary)

    def bounties(self):
        target = 'bounties'
        text = 'Bounties'
        summary = 'The Launchpad Universal Bounty Tracker'
        return Link(target, text, summary)

    def calendar(self):
        target = 'calendar'
        text = 'Calendar'
        return Link(target, text)


class RosettaAppMenus(ApplicationMenu):
    usedfor = IRosettaApplication
    facet = 'translations'
    links = ['overview', 'about', 'preferences']

    def overview(self):
        target = ''
        text = 'Translations'
        return Link(target, text)

    def upload(self):
        target = '+upload'
        text = 'Upload'
        return Link(target, text)

    def download(self):
        target = '+export'
        text = 'Download'
        return Link(target, text)

    def about(self):
        target = '+about'
        text = 'About Rosetta'
        return Link(target, text)

    def preferences(self):
        target = 'prefs'
        text = 'Preferences'
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

        # If we have a query string, remove some things we don't want, and
        # keep it around.
        if query_string:
            query_dict = cgi.parse_qs(query_string, keep_blank_values=True)
            query_dict.pop('loggingout', None)
            query_string = urllib.urlencode(
                sorted(query_dict.items()), doseq=True)
            # If we still have a query_string after things we don't want
            # have been removed, add it onto the url.
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
