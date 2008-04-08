# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""Implementation of the ws: namespace in TALES."""

__metaclass__ = type

from canonical.launchpad.webapp import canonical_url

class WebServiceAPI:
    "Namespace for web service-related functions."

    def __init__(self, context):
        self.context = context

    def url(self):
        """Return the full URL to the object."""
        return canonical_url(self.context)
