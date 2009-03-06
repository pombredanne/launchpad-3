# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A configuration class describing the Launchpad web service."""

__metaclass__ = type
__all__ = [
    'LaunchpadWebServiceConfiguration',
]

from zope.interface import implements

from canonical.lazr.interfaces.rest import IWebServiceConfiguration

from canonical.launchpad import versioninfo

class LaunchpadWebServiceConfiguration:
    implements(IWebServiceConfiguration)

    view_permission = "launchpad.View"

    service_version_uri_prefix = "beta"

    @property
    def code_revision(self):
        return str(versioninfo.revno)
