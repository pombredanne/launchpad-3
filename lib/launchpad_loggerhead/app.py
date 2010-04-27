# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import logging
import re
import os
import threading
import urllib
import urlparse
import xmlrpclib

from bzrlib import branch, errors, lru_cache, urlutils

from loggerhead.apps import favicon_app, static_app
from loggerhead.apps.branch import BranchWSGIApp

from openid.extensions.sreg import SRegRequest, SRegResponse
from openid.consumer.consumer import CANCEL, Consumer, FAILURE, SUCCESS
from openid.store.memstore import MemoryStore

from paste.fileapp import DataApp
from paste.request import construct_url, parse_querystring, path_info_pop
from paste.httpexceptions import (
    HTTPMovedPermanently, HTTPNotFound, HTTPUnauthorized)

from canonical.config import config
from canonical.launchpad.xmlrpc import faults
from lp.code.interfaces.codehosting import (
    BRANCH_TRANSPORT, LAUNCHPAD_ANONYMOUS, LAUNCHPAD_SERVICES)
from lp.codehosting.vfs import branch_id_to_path

robots_txt = '''\
User-agent: *
Disallow: /
'''

robots_app = DataApp(robots_txt, content_type='text/plain')


thread_transports = threading.local()

def valid_launchpad_name(s):
    return re.match('^[a-z0-9][a-z0-9\+\.\-]*$', s) is not None


def valid_launchpad_user_name(s):
    return re.match('^~[a-z0-9][a-z0-9\+\.\-]*$', s) is not None


def valid_launchpad_branch_name(s):
    return re.match(r'^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z', s) is not None


class RootApp:

    def __init__(self, session_var):
        self.graph_cache = lru_cache.LRUCache(10)
        self.branchfs = xmlrpclib.ServerProxy(
            config.codehosting.branchfs_endpoint)
        self.session_var = session_var
        self.store = MemoryStore()
        self.log = logging.getLogger('lp-loggerhead')
        branch.Branch.hooks.install_named_hook(
            'transform_fallback_location',
            self._transform_fallback_location_hook,
            'RootApp._transform_fallback_location_hook')

    def _transform_fallback_location_hook(self, branch, url):
        """Transform a human-readable fallback URL into and id-based one.

        Branches on Launchpad record their stacked-on URLs in the form
        '/~user/product/branch', but we need to access branches based on
        database ID to gain access to private branches.  So we use this hook
        into Bazaar's branch-opening process to translate the former to the
        latter.
        """
        # It might seem that using the LAUNCHPAD_SERVICES 'user', which allows
        # access to all branches, here would be a security risk.  But in fact
        # it isn't, because a user will only have launchpad.View on the
        # stacked branch if they have it for all the stacked-on branches.
        # (It would be nice to use the user from the request, but that's far
        # from simple because branch hooks are global per-process and we
        # handle different requests in different threads).
        transport_type, info, trail = self.branchfs.translatePath(
            LAUNCHPAD_SERVICES, url)
        return urlparse.urljoin(
            config.codehosting.internal_branch_by_id_root,
            branch_id_to_path(info['id']))

    def get_transports(self):
        t = getattr(thread_transports, 'transports', None)
        if t is None:
            thread_transports.transports = []
        return thread_transports.transports

    def _make_consumer(self, environ):
        """Build an OpenID `Consumer` object with standard arguments."""
        return Consumer(environ[self.session_var], self.store)

    def _begin_login(self, environ, start_response):
        """Start the process of authenticating with OpenID.

        We redirect the user to Launchpad to identify themselves, asking to be
        sent their nickname.  Launchpad will then redirect them to our +login
        page with enough information that we can then redirect them again to
        the page they were looking at, with a cookie that gives us the
        username.
        """
        openid_request = self._make_consumer(environ).begin(
            'https://' + config.vhost.openid.hostname)
        openid_request.addExtension(
            SRegRequest(required=['nickname']))
        back_to = construct_url(environ)
        raise HTTPMovedPermanently(openid_request.redirectURL(
            config.codehosting.secure_codebrowse_root,
            config.codehosting.secure_codebrowse_root + '+login/?'
            + urllib.urlencode({'back_to':back_to})))

    def _complete_login(self, environ, start_response):
        """Complete the OpenID authentication process.

        Here we handle the result of the OpenID process.  If the process
        succeeded, we record the username in the session and redirect the user
        to the page they were trying to view that triggered the login attempt.
        In the various failures cases we return a 401 Unauthorized response
        with a brief explanation of what went wrong.
        """
        query = dict(parse_querystring(environ))
        # Passing query['openid.return_to'] here is massive cheating, but
        # given we control the endpoint who cares.
        response = self._make_consumer(environ).complete(
            query, query['openid.return_to'])
        if response.status == SUCCESS:
            self.log.error('open id response: SUCCESS')
            sreg_info = SRegResponse.fromSuccessResponse(response)
            environ[self.session_var]['user'] = sreg_info['nickname']
            raise HTTPMovedPermanently(query['back_to'])
        elif response.status == FAILURE:
            self.log.error('open id response: FAILURE: %s', response.message)
            exc = HTTPUnauthorized()
            exc.explanation = response.message
            raise exc
        elif response.status == CANCEL:
            self.log.error('open id response: CANCEL')
            exc = HTTPUnauthorized()
            exc.explanation = "Authetication cancelled."
            raise exc
        else:
            self.log.error('open id response: UNKNOWN')
            exc = HTTPUnauthorized()
            exc.explanation = "Unknown OpenID response."
            raise exc

    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        if environ['PATH_INFO'].startswith('/static/'):
            path_info_pop(environ)
            return static_app(environ, start_response)
        elif environ['PATH_INFO'] == '/favicon.ico':
            return favicon_app(environ, start_response)
        elif environ['PATH_INFO'] == '/robots.txt':
            return robots_app(environ, start_response)
        elif environ['PATH_INFO'].startswith('/+login'):
            return self._complete_login(environ, start_response)
        path = environ['PATH_INFO']
        trailingSlashCount = len(path) - len(path.rstrip('/'))
        user = environ[self.session_var].get('user', LAUNCHPAD_ANONYMOUS)
        try:
            transport_type, info, trail = self.branchfs.translatePath(
                user, urlutils.escape(path))
        except xmlrpclib.Fault, f:
            if faults.check_fault(f, faults.PathTranslationError):
                raise HTTPNotFound()
            elif faults.check_fault(f, faults.PermissionDenied):
                # If we're not allowed to see the branch...
                if environ['wsgi.url_scheme'] != 'https':
                    # ... the request shouldn't have come in over http, as
                    # requests for private branches over http should be
                    # redirected to https by the dynamic rewrite script we use
                    # (which runs before this code is reached), but just in
                    # case...
                    env_copy = environ.copy()
                    env_copy['wsgi.url_scheme'] = 'https'
                    raise HTTPMovedPermanently(construct_url(env_copy))
                elif user != LAUNCHPAD_ANONYMOUS:
                    # ... if the user is already logged in and still can't see
                    # the branch, they lose.
                    exc = HTTPUnauthorized()
                    exc.explanation = "You are logged in as %s." % user
                    raise exc
                else:
                    # ... otherwise, lets give them a chance to log in with
                    # OpenID.
                    return self._begin_login(environ, start_response)
            else:
                raise
        if transport_type != BRANCH_TRANSPORT:
            raise HTTPNotFound()
        trail = urlutils.unescape(trail).encode('utf-8')
        trail += trailingSlashCount * '/'
        amount_consumed = len(path) - len(trail)
        consumed = path[:amount_consumed]
        branch_name = consumed.strip('/')
        self.log.info('Using branch: %s', branch_name)
        if trail and not trail.startswith('/'):
            trail = '/' + trail
        environ['PATH_INFO'] = trail
        environ['SCRIPT_NAME'] += consumed.rstrip('/')
        branch_url = urlparse.urljoin(
            config.codehosting.internal_branch_by_id_root,
            branch_id_to_path(info['id']))
        branch_link = urlparse.urljoin(
            config.codebrowse.launchpad_root, branch_name)
        cachepath = os.path.join(
            config.codebrowse.cachepath, branch_name[1:])
        if not os.path.isdir(cachepath):
            os.makedirs(cachepath)
        self.log.info('branch_url: %s', branch_url)
        try:
            bzr_branch = branch.Branch.open(
                branch_url, possible_transports=self.get_transports())
        except errors.NotBranchError, err:
            self.log.warning('Not a branch: %s', err)
            raise HTTPNotFound()
        bzr_branch.lock_read()
        try:
            view = BranchWSGIApp(
                bzr_branch, branch_name, {'cachepath': cachepath},
                self.graph_cache, branch_link=branch_link, served_url=None)
            return view.app(environ, start_response)
        finally:
            bzr_branch.unlock()
