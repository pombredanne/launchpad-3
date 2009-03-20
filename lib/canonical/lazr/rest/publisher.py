# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Publisher mixins for the webservice.

This module defines classes that are usually needed for integration
with the Zope publisher.
"""

__metaclass__ = type
__all__ = [
    'browser_request_to_web_service_request',
    'WebServicePublicationMixin',
    'WebServiceRequestTraversal',
    ]

import urllib

from zope.component import (
    adapter, getMultiAdapter, getUtility, queryAdapter, queryMultiAdapter)
from zope.interface import alsoProvides, implementer, implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.interfaces import IBytes
from zope.security.checker import ProxyFactory

from lazr.uri import URI

from canonical.lazr.interfaces.rest import (
    IByteStorage, ICollection, IEntry, IEntryField, IHTTPResource,
    IWebBrowserInitiatedRequest, IWebServiceClientRequest,
    IWebServiceConfiguration)
from canonical.lazr.interfaces.fields import ICollectionField
from canonical.lazr.rest.resource import (
    CollectionResource, EntryField, EntryFieldResource,
    EntryResource, ScopedCollection)


class WebServicePublicationMixin:
    """A mixin for webservice publication.

    This should usually be mixed-in with ZopePublication, or Browser,
    or HTTPPublication"""


    def traverseName(self, request, ob, name):
        """See `zope.publisher.interfaces.IPublication`.

        In addition to the default traversal implementation, this publication
        also handles traversal to collection scoped into an entry.
        """
        # If this is the last traversal step, then look first for a scoped
        # collection. This is done because although Navigation handles
        # traversal to entries in a scoped collection, they don't usually
        # handle traversing to the scoped collection itself.
        if len(request.getTraversalStack()) == 0:
            try:
                entry = IEntry(ob)
            except TypeError:
                pass
            else:
                field = entry.schema.get(name)
                if ICollectionField.providedBy(field):
                    result = self._traverseToScopedCollection(
                        request, entry, field, name)
                    if result is not None:
                        return result
                elif IBytes.providedBy(field):
                    return self._traverseToByteStorage(
                        request, entry, field, name)
                elif field is not None:
                    return EntryField(entry, field, name)
                else:
                    # Falls through to our parent version.
                    pass
        return super(WebServicePublicationMixin, self).traverseName(
            request, ob, name)

    def _traverseToByteStorage(self, request, entry, field, name):
        """Try to traverse to a byte storage resource in entry."""
        # Even if the library file is None, we want to allow
        # traversal, because the request might be a PUT request
        # creating a file here.
        return getMultiAdapter((entry, field.bind(entry)), IByteStorage)

    def _traverseToScopedCollection(self, request, entry, field, name):
        """Try to traverse to a collection in entry.

        This is done because we don't usually traverse to attributes
        representing a collection in our regular Navigation.

        This method returns None if a scoped collection cannot be found.
        """
        collection = getattr(entry, name, None)
        if collection is None:
            return None
        scoped_collection = ScopedCollection(entry.context, entry)
        # Tell the IScopedCollection object what collection it's managing,
        # and what the collection's relationship is to the entry it's
        # scoped to.
        scoped_collection.collection = collection
        scoped_collection.relationship = field
        return scoped_collection

    def getDefaultTraversal(self, request, ob):
        """See `zope.publisher.interfaces.browser.IBrowserPublication`.

        The WebService doesn't use the getDefaultTraversal() extension
        mechanism, because it only applies to GET, HEAD, and POST methods.

        See getResource() for the alternate mechanism.
        """
        # Don't traverse to anything else.
        return ob, None

    def getResource(self, request, ob):
        """Return the resource that can publish the object ob.

        This is done at the end of traversal.  If the published object
        supports the ICollection, or IEntry interface we wrap it into the
        appropriate resource.
        """
        if (ICollection.providedBy(ob) or
            queryAdapter(ob, ICollection) is not None):
            # Object supports ICollection protocol.
            resource = CollectionResource(ob, request)
        elif (IEntry.providedBy(ob) or
              queryAdapter(ob, IEntry) is not None):
            # Object supports IEntry protocol.
            resource = EntryResource(ob, request)
        elif (IEntryField.providedBy(ob) or
              queryAdapter(ob, IEntryField) is not None):
            # Object supports IEntryField protocol.
            resource = EntryFieldResource(ob, request)
        elif queryMultiAdapter((ob, request), IHTTPResource) is not None:
            # Object can be adapted to a resource.
            resource = queryMultiAdapter((ob, request), IHTTPResource)
        elif IHTTPResource.providedBy(ob):
            # A resource knows how to take care of itself.
            return ob
        elif request.response.getStatus() != 599:
            # The request was handled by the traversal code itself. Do
            # nothing.
            return ob
        else:
            # This object should not be published on the web service.
            raise NotFound(ob, '')

        # Wrap the resource in a security proxy.
        return ProxyFactory(resource)

    def callObject(self, request, object):
        """Help web browsers handle redirects correctly."""
        value = super(
            WebServicePublicationMixin, self).callObject(request, object)
        if request.response.getStatus() / 100 == 3:
            vhost = URI(request.getApplicationURL()).host
            if IWebBrowserInitiatedRequest.providedBy(request):
                # This request was (probably) sent by a web
                # browser. Because web browsers, content negotiation,
                # and redirects are a deadly combination, we're going
                # to help the browser out a little.
                #
                # We're going to take the current request's "Accept"
                # header and put it into the URL specified in the
                # Location header. When the web browser makes its
                # request, it will munge the original 'Accept' header,
                # but because the URL it's accessing will include the
                # old header in the "ws.accept" header, we'll still be
                # able to serve the right document.
                location = request.response.getHeader("Location", None)
                if location is not None:
                    accept = request.response.getHeader(
                        "Accept", "application/json")
                    qs_append = "ws.accept=" + urllib.quote(accept)
                    uri = URI(location)
                    if uri.query is None:
                        uri.query = qs_append
                    else:
                        uri.query += '&' + qs_append
                    request.response.setHeader("Location", str(uri))
        return value


class WebServiceRequestTraversal:
    """Mixin providing web-service resource wrapping in traversal.

    This should be mixed in the request using to the base publication used.
    """
    implements(IWebServiceClientRequest)

    def traverse(self, ob):
        """See `zope.publisher.interfaces.IPublisherRequest`.

        This is called once at the beginning of the traversal process.

        WebService requests call the `WebServicePublication.getResource()`
        on the result of the base class's traversal.
        """
        self._removeVirtualHostTraversals()
        result = super(WebServiceRequestTraversal, self).traverse(ob)
        return self.publication.getResource(self, result)

    def _removeVirtualHostTraversals(self):
        """Remove the /[path_override] and /[version] traversal names."""
        names = list()
        config = getUtility(IWebServiceConfiguration)
        api = self._popTraversal(config.path_override)
        if api is not None:
            names.append(api)
            # Requests that use the webservice path override are
            # usually made by web browsers. Mark this request as one
            # initiated by a web browser, for the sake of
            # optimizations later in the request lifecycle.
            alsoProvides(self, IWebBrowserInitiatedRequest)

        # Only accept versioned URLs.
        version_string = config.service_version_uri_prefix
        version = self._popTraversal(version_string)
        if version is not None:
            names.append(version)
            self.setVirtualHostRoot(names=names)
        else:
            raise NotFound(self, '', self)

    def _popTraversal(self, name):
        """Remove a name from the traversal stack, if it is present.

        :return: The name of the element removed, or None if the stack
            wasn't changed.
        """
        stack = self.getTraversalStack()
        if len(stack) > 0 and stack[-1] == name:
            item = stack.pop()
            self.setTraversalStack(stack)
            return item
        return None


@implementer(IWebServiceClientRequest)
@adapter(IBrowserRequest)
def browser_request_to_web_service_request(website_request):
    """An adapter from a browser request to a web service request.

    Used to instantiate Resource objects when handling normal web
    browser requests.
    """
    config = getUtility(IWebServiceConfiguration)
    body = website_request.bodyStream.getCacheStream().read()
    environ = dict(website_request.environment)
    # Zope picks up on SERVER_URL when setting the _app_server attribute
    # of the new request.
    environ['SERVER_URL'] = website_request.getApplicationURL()
    web_service_request = config.createRequest(body, environ)
    web_service_request.setVirtualHostRoot(
        names=[config.path_override, config.service_version_uri_prefix])
    web_service_request._vh_root = website_request.getVirtualHostRoot()
    return web_service_request


