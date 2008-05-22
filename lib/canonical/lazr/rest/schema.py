# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Schema extensions for HTTP resources."""

__metaclass__ = type
__all__ = [
    'CollectionField',
    'CollectionFieldMarshaller',
    'DateTimeFieldMarshaller',
    'ObjectLookupFieldMarshaller',
    'SimpleFieldMarshaller',
    'SimpleVocabularyLookupFieldMarshaller',
    'URLDereferencingMixin',
    'VocabularyLookupFieldMarshaller',
    ]

from datetime import datetime
import pytz
import urllib
import urlparse
from StringIO import StringIO

from zope.app.datetimeutils import (
    DateError, DateTimeError, DateTimeParser, SyntaxError)
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema._field import AbstractCollection
from zope.security.proxy import removeSecurityProxy

from canonical.config import config

from canonical.launchpad.layers import WebServiceLayer, setFirstLayer
from canonical.launchpad.webapp import canonical_url

from canonical.lazr.interfaces.rest import ICollectionField
from canonical.lazr.interfaces.field import IFieldMarshaller


class CollectionField(AbstractCollection):
    """A collection associated with an entry."""
    # We subclass AbstractCollection instead of List because List
    # has a _type of list, and we don't want to have to implement list
    # semantics for this class.
    implements(ICollectionField)

    def __init__(self, *args, **kwargs):
        """A generic collection field.

        The readonly property defaults to True since these fields are usually
        for collections of things linked to an object, and these collections
        are managed through a dedicated API.
        """
        kwargs.setdefault('readonly', True)
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


class SimpleFieldMarshaller:
    """A marshaller that returns the same value it's served."""
    implements(IFieldMarshaller)

    def __init__(self, field, request):
        self.field = field
        self.request = request

    def marshall_from_json_data(self, value):
        "Do nothing to the value."
        return value

    def marshall_from_string(self, value):
        "Make sure the value is a string and then call a hook method."
        if value is None:
            return None
        assert isinstance(value, basestring), 'Marshalling a non-string'
        return self._marshall_from_string(value)

    def _marshall_from_string(self, value):
        """If the value is empty, return None. Otherwise return the value."""
        if value == "":
            return None
        return value

    def representationName(self, field_name):
        "Return the field name as is."
        return field_name

    def unmarshall(self, entry, field_name, value):
        "Return the value as is."
        return value


class DateTimeFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that transforms its value into a datetime object."""

    def marshall_from_json_data(self, value):
        """The JSON value is a string that needs to be parsed."""
        return self.marshall_from_string(value)

    def _marshall_from_string(self, value):
        """Parse the value as a datetime object."""
        try:
            value = DateTimeParser().parse(value)
            (year, month, day, hours, minutes, secondsAndMicroseconds,
             timezone) = value
            seconds = int(secondsAndMicroseconds)
            microseconds = int(
                round((secondsAndMicroseconds - seconds) * 1000000))
            if timezone not in ['Z', '+0000', '-0000']:
                raise ValueError("Time not in UTC.")
            return datetime(year, month, day, hours, minutes,
                            seconds, microseconds, pytz.utc)
        except (DateError, DateTimeError, SyntaxError):
            raise ValueError("Value doesn't look like a date.")


class CollectionFieldMarshaller(SimpleFieldMarshaller):

    def representationName(self, field_name):
        "Make it clear that the value is a link to a collection."
        return field_name + '_collection_link'

    def marshall_from_json_data(self, value):
        """The JSON value is a string that needs to be dereferenced."""
        if value is None:
            return None
        return self._marshall_from_string(value)

    def unmarshall(self, entry, field_name, value):
        return "%s/%s" % (canonical_url(entry.context), field_name)


def VocabularyLookupFieldMarshaller(field, request):
    """A marshaller that uses the underlying vocabulary.

    This is just a factory function that does another adapter lookup
    for a marshaller, one that can take into account the vocabulary
    in addition to the field type (presumably Choice) and the request.
    """
    return getMultiAdapter((field, request, field.vocabulary),
                           IFieldMarshaller)


class SimpleVocabularyLookupFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller for vocabulary lookup by title."""

    def __init__(self, field, request, vocabulary):
        """Initialize the marshaller with the vocabulary it'll use."""
        super(SimpleVocabularyLookupFieldMarshaller, self).__init__(
            field, request)
        self.vocabulary = vocabulary

    def _marshall_from_string(self, value):
        """Find an item in the vocabulary by title."""
        valid_titles = []
        for item in self.field.vocabulary.items:
            if item.title == value:
                return item
            valid_titles.append(item.title)
        raise ValueError(
            'Invalid value "%s". Acceptable values are: %s' %
            (value, ', '.join(valid_titles)))


class ObjectLookupFieldMarshaller(SimpleVocabularyLookupFieldMarshaller,
                                  URLDereferencingMixin):
    """A marshaller that turns URLs into data model objects.

    This marshaller can be used with a IChoice field (initialized
    with a vocabulary) or with an IObject field (no vocabulary).
    """

    def __init__(self, field, request, vocabulary=None):
        super(ObjectLookupFieldMarshaller, self).__init__(
            field, request, vocabulary)

    def representationName(self, field_name):
        "Make it clear that the value is a link to an object, not an object."
        return field_name + '_link'

    def unmarshall(self, entry, field_name, value):
        "Represent an object as the URL to that object"
        repr_value = None
        if value is not None:
            repr_value = canonical_url(value)
        return repr_value

    def marshall_from_json_data(self, value):
        """The JSON value is a string that needs to be dereferenced."""
        if value is None:
            return None
        return self._marshall_from_string(value)

    def _marshall_from_string(self, value):
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
