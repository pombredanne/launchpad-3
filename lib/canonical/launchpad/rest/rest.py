# Copyright 2008 Canonical Ltd.  All rights reserved.
"""HTTP resources exposed by Launchpad's RESTful web service."""

__metaclass__ = type

__all__ = [
    'HelloWorldResource',
]

from canonical.lazr.rest import (HTTPResource)

class HelloWorldResource(HTTPResource):

    def __call__(self):
        """Return a string in response to GET."""
        if self.request.method == "GET":
            return "Hello, world!"
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET")

