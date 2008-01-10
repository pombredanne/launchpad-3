# Copyright 2008 Canonical Ltd.  All rights reserved.

"""HTTP resources exposed by Launchpad's RESTful web service."""

__metaclass__ = type
__all__ = [
    'ServiceRootResource',
    ]


from canonical.lazr.rest import ReadOnlyResource


class ServiceRootResource(ReadOnlyResource):
    """A resource that responds to GET by describing the service."""

    def do_GET(self, request):
        """Return a description of the resource."""
        return "This is Launchpad's web service."
