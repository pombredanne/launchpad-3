# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Helpers for testing out publication related code."""

__metaclass__ = type
__all__ = [
    'get_request_and_publication',
    'print_request_and_publication',
    ]

from cStringIO import StringIO

# Z3 doesn't make this available as a utility.
from zope.app.publication.requestpublicationregistry import factoryRegistry
from canonical.launchpad.webapp.servers import ProtocolErrorPublication

# Defines an helper function that returns the appropriate
# IRequest and IPublication.
def get_request_and_publication(host='localhost', port=None,
                                method='GET', mime_type='text/html',
                                in_stream='', extra_environment=None):
    """Helper method that return the IRequest and IPublication for a request.

    This method emulates what the Zope publisher would do to find the request
    and publication class for a particular environment.
    """
    environment = {'HTTP_HOST': host,
                   'REQUEST_METHOD': method,
                   'SERVER_PORT': port,
                   'CONTENT_TYPE': mime_type}
    if extra_environment is not None:
        environment.update(extra_environment)
    launchpad_factory = factoryRegistry.lookup(
        method, mime_type, environment)
    request_factory, publication_factory = launchpad_factory()
    request = request_factory(StringIO(in_stream), environment)
    # Since Launchpad doesn't use ZODB, we use None here.
    publication = publication_factory(None)
    return request, publication

def print_request_and_publication(host='localhost', port=None,
                                  method='GET',
                                  mime_type='text/html',
                                  extra_environment=None):
    """Helper giving short names for the request and publication."""
    request, publication = get_request_and_publication(
        host, port, method, mime_type,
        extra_environment=extra_environment)
    print type(request).__name__.split('.')[-1]
    publication_classname = type(publication).__name__.split('.')[-1]
    if isinstance(publication, ProtocolErrorPublication):
        print "%s: status=%d" % (
            publication_classname, publication.status)
        for name, value in publication.headers.items():
            print "  %s: %s" % (name, value)
    else:
        print publication_classname
