# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A configuration class describing the Launchpad web service."""

__metaclass__ = type
__all__ = [
    'LaunchpadWebServiceConfiguration',
]

from zope.component import getUtility

from lazr.restful.simple import BaseWebServiceConfiguration
from lp.services.memcache.client import memcache_client_factory

from canonical.config import config
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.servers import (
    WebServiceClientRequest, WebServicePublication)

from canonical.launchpad import versioninfo

class RepresentationCache(dict):

    def __setitem__(self, key, value):
        super(RepresentationCache, self).__setitem__(key, value)


class MemcachedRepresentationCache:

    def __init__(self):
        self.client = memcache_client_factory()

    def key_for(self, obj):
        import pdb; pdb.set_trace()

    def get(self, key, default=None):
        return self.client.get(key.encode('utf-8')) or default

    def __setitem__(self, key, value):
        self.client.set(key.encode('utf-8'), value)

    def __delitem__(self, key):
        self.client.delete(key.encode('utf-8'))

class LaunchpadWebServiceConfiguration(BaseWebServiceConfiguration):

    path_override = "api"
    active_versions = ["beta", "1.0", "devel"]
    last_version_with_mutator_named_operations = "beta"
    view_permission = "launchpad.View"
    compensate_for_mod_compress_etag_modification = True

    service_description = """The Launchpad web service allows automated
        clients to access most of the functionality available on the
        Launchpad web site. For help getting started, see
        <a href="https://help.launchpad.net/API/">the help wiki.</a>"""

    version_descriptions = {
        "beta": """This is the first version of the web service ever
        published. Its end-of-life date is April 2011, the same as the
        Ubuntu release "Karmic Koala".""",

        "1.0": """This version of the web service removes unnecessary
        named operations. It was introduced in March 2010, and its
        end-of-life date is April 2015, the same as the server version
        of the Ubuntu release "Lucid Lynx".""",

        "devel": """This version of the web service reflects the most
        recent changes made. It may abruptly change without
        warning. Periodically, these changes are bundled up and given a
        permanent version number.""" }

    @property
    def use_https(self):
        return config.vhosts.use_https

    @property
    def code_revision(self):
        return str(versioninfo.revno)

    def createRequest(self, body_instream, environ):
        """See `IWebServiceConfiguration`."""
        request = WebServiceClientRequest(body_instream, environ)
        request.setPublication(WebServicePublication(None))
        return request

    @property
    def default_batch_size(self):
        return 80 #config.launchpad.default_batch_size

    @property
    def max_batch_size(self):
        return config.launchpad.max_batch_size

    @property
    def show_tracebacks(self):
        """See `IWebServiceConfiguration`.

        People who aren't developers shouldn't be shown any
        information about the exception that caused an internal server
        error. It might contain private information.
        """
        is_developer = getUtility(ILaunchBag).developer
        return (is_developer or config.canonical.show_tracebacks)

    def get_request_user(self):
        """See `IWebServiceConfiguration`."""
        return getUtility(ILaunchBag).user
