# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Schema extensions for HTTP resources."""

__metaclass__ = type
__all__ = [
    'CollectionField',
    'IntFieldDeserializer',
    'ObjectLookupFieldDeserializer',
    'SimpleFieldDeserializer',
    'SimpleVocabularyLookupFieldDeserializer',
    'URLDereferencingMixin',
    'VocabularyLookupFieldDeserializer',
    ]


import urllib
import urlparse
from StringIO import StringIO

from zope.component import getMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema._field import AbstractCollection
from zope.security.proxy import removeSecurityProxy

from canonical.config import config

from canonical.launchpad.layers import WebServiceLayer, setFirstLayer

from canonical.lazr.interfaces.rest import ICollectionField
from canonical.lazr.interfaces.field import IFieldDeserializer


class CollectionField(AbstractCollection):
    """A collection associated with an entry."""
    # We subclass AbstractCollection instead of List because List
    # has a _type of list, and we don't want to have to implement list
    # semantics for this class.
    implements(ICollectionField)

    def __init__(self, *args, **kwargs):
        """Define a container object that's related to some other object.

        This will show up in the web service as a scoped collection.

        :param is_entry_container: By default, scoped collections
        contain references to entries whose self_link URLs are handled
        by the data type's parent_collection_path. Set this to True if
        the self_link URL of an entry should be handled by the scoped
        collection.
        """

        self.is_entry_container = kwargs.pop('is_entry_container', False)
        super(CollectionField, self).__init__(*args, **kwargs)


class URLDereferencingMixin:
    """A mixin for any class that dereferences URLs into objects."""

    def dereference_url(self, url):
        """Look up a resource in the web service by URL.

        Representations and custom operations use URLs to refer to
        resources in the web service. When processing an incoming
        representation or custom operation it's often necessary to see
        which object a URL refers to. This method calls the URL
        traversal code to dereference a URL into a published object.

        :param url: The URL to a resource.
        :raise NotFoundError: If the URL does not designate a
            published object.
        """
        (protocol, host, path, query, fragment) = urlparse.urlsplit(url)

        request_host = self.request.get('HTTP_HOST')
        if config.vhosts.use_https:
            site_protocol = 'https'
        else:
            site_protocol = 'http'

        if (host != request_host or protocol != site_protocol or
            query != '' or fragment != ''):
            raise NotFound(self, url, self.request)

        path_parts = [urllib.unquote(part) for part in path.split('/')]
        path_parts.pop(0)
        path_parts.reverse()

        # Import here is neccessary to avoid circular import.
        from canonical.launchpad.webapp.servers import WebServiceClientRequest
        request = WebServiceClientRequest(StringIO(), {'PATH_INFO' : path})
        setFirstLayer(request, WebServiceLayer)
        request.setTraversalStack(path_parts)

        publication = self.request.publication
        request.setPublication(publication)
        return request.traverse(publication.getApplication(self.request))


class SimpleFieldDeserializer:
    """A deserializer that returns the same value it's served.

    The only exception is that the empty string is treated as the lack
    of a value; i.e. None.
    """
    implements(IFieldDeserializer)

    def __init__(self, field, request):
        self.field = field
        self.request = request

    def deserialize(self, value):
        "Make sure the value is a string and then call _deserialize()."
        assert isinstance(value, basestring), 'Deserializing a non-string'
        return self._deserialize(value)

    def _deserialize(self, value):
        """Return the value as is, unless it's empty; then return None."""
        if value == "":
            return None
        return value


class IntFieldDeserializer(SimpleFieldDeserializer):
    """A deserializer that transforms its value into an integer."""

    def _deserialize(self, value):
        """Try to convert the value into an integer."""
        return int(value)


def VocabularyLookupFieldDeserializer(field, request):
    """A deserializer that uses the underlying vocabulary.

    This is just a factory function that does another adapter lookup
    for a deserializer, one that can take into account the vocabulary
    in addition to the field type (presumably Choice) and the request.
    """

    return getMultiAdapter((field, field.vocabulary, request),
                           IFieldDeserializer)


class SimpleVocabularyLookupFieldDeserializer(SimpleFieldDeserializer):
    """A deserializer for vocabulary lookup by title."""

    def __init__(self, field, vocabulary, request):
        """Initialize the deserializer with the vocabulary it'll use."""
        super(SimpleVocabularyLookupFieldDeserializer, self).__init__(
            field, request)
        self.vocabulary = vocabulary

    def _deserialize(self, value):
        """Find an item in the vocabulary by title."""
        valid_titles = []
        for item in self.field.vocabulary.items:
            if item.title == value:
                return item
            valid_titles.append(item.title)
        raise ValueError(
            'Invalid value "%s". Acceptable values are: %s' %
            (value, ', '.join(valid_titles)))


class ObjectLookupFieldDeserializer(SimpleVocabularyLookupFieldDeserializer,
                                    URLDereferencingMixin):
    """A deserializer that turns URLs into data model objects."""

    def _deserialize(self, value):
        """Look up the data model object by URL."""
        try:
            resource = self.dereference_url(value)
        except NotFound:
            # The URL doesn't correspond to any real object.
            raise ValueError('No such object "%s".' % value)
        # We looked up the URL and got the thing at the other end of
        # the URL: a resource. But internally, a resource isn't a
        # valid value for any schema field. Instead we want the object
        # that serves as a resource's context. Any time we want to get
        # to the object underlying a resource, we need to strip its
        # security proxy.
        return removeSecurityProxy(resource).context
