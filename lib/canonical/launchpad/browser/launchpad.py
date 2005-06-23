# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser code for the launchpad application."""

__metaclass__ = type
__all__ = ['LoginStatus']

from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag

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
        url = self.request.getURL()
        path_info = self.request['PATH_INFO']
        # Make the URL stop at the end of path_info so that we don't get
        # spurious '+index' at the end.
        full_url = '%s%s' % (url[:url.find(path_info)], path_info)
        if full_url.endswith('/'):
            full_url = full_url[:-1]
        logout_url_end = '/+logout'
        if full_url.endswith(logout_url_end):
            full_url = full_url[:-len(logout_url_end)]
        return '%s/+login%s' % (full_url, query_string)

