# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Schema extensions for HTTP resources."""

__metaclass__ = type
__all__ = [
    'AbstractCollectionFieldMarshaller',
    'BoolFieldMarshaller',
    'BytesFieldMarshaller',
    'CollectionField',
    'CollectionFieldMarshaller',
    'DateTimeFieldMarshaller',
    'FloatFieldMarshaller',
    'IntFieldMarshaller',
    'ObjectLookupFieldMarshaller',
    'Reference',
    'SimpleFieldMarshaller',
    'SimpleVocabularyLookupFieldMarshaller',
    'TextFieldMarshaller',
    'TokenizedVocabularyFieldMarshaller',
    'URLDereferencingMixin',
    'VocabularyLookupFieldMarshaller',
    ]

from datetime import datetime
import pytz
from StringIO import StringIO
import urllib

import simplejson

from zope.app.datetimeutils import (
    DateError, DateTimeError, DateTimeParser, SyntaxError)
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema import Field, Object
from zope.schema._field import AbstractCollection
from zope.schema.interfaces import SchemaNotProvided
from zope.security.proxy import removeSecurityProxy

from canonical.config import config

from canonical.launchpad.layers import WebServiceLayer, setFirstLayer
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.url import urlsplit

from canonical.lazr.interfaces.rest import ICollectionField
from canonical.lazr.interfaces.field import IFieldMarshaller
from canonical.lazr.utils import safe_hasattr


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
        :raise NotFound: If the URL does not designate a
            published object.
        """
        (protocol, host, path, query, fragment) = urlsplit(url)

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

        # Import here is necessary to avoid circular import.
        from canonical.launchpad.webapp.servers import WebServiceClientRequest
        request = WebServiceClientRequest(StringIO(), {'PATH_INFO' : path})
        setFirstLayer(request, WebServiceLayer)
        request.setTraversalStack(path_parts)

        publication = self.request.publication
        request.setPublication(publication)
        return request.traverse(publication.getApplication(self.request))


class SimpleFieldMarshaller:
    """A marshaller that returns the same value it's served.

    This implementation is meant to be subclassed.
    """
    implements(IFieldMarshaller)


    # Set this to type or tuple of types that the JSON value must be of.
    _type = None

    # The error message to use if the isinstance fails on the _type. The
    # value will be interpreted in the message.
    _type_error_message = None

    def __init__(self, field, request):
        self.field = field
        self.request = request

    def marshall_from_json_data(self, value):
        """See `IFieldMarshaller`.

        When value is None, return None, otherwise call
        _marshall_from_json_data().
        """
        if value is None:
            return None
        return self._marshall_from_json_data(value)

    def marshall_from_request(self, value):
        """See `IFieldMarshaller`.

        Try to decode value as a JSON-encoded string and pass it on to
        _marshall_from_request() if it's not None. If value isn't a
        JSON-encoded string, interpret it as string literal.
        """
        try:
            value = simplejson.loads(value)
        except (ValueError, TypeError):
            # Pass the value as is. This saves client from having to encode
            # strings.
            pass
        if value is None:
            return None
        return self._marshall_from_request(value)

    def _marshall_from_request(self, value):
        """Hook method to marshall a non-null JSON value.

        Default is to just call _marshall_from_json_data() with the value.
        """
        return self._marshall_from_json_data(value)

    def _marshall_from_json_data(self, value):
        """Hook method to marshall a no-null value.

        Default is to return the value unchanged.
        """
        if self._type is not None:
            if not isinstance(value, self._type):
                raise ValueError(self._type_error_message % value)
        return value

    @property
    def representation_name(self):
        """See `IFieldMarshaller`.

        Return the field name as is.
        """
        return self.field.__name__

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        Return the value as is.
        """
        return value


class BoolFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that transforms its value into an integer."""

    _type = bool
    _type_error_message = 'not a boolean: %r'


class IntFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that transforms its value into an integer."""

    _type = int
    _type_error_message = 'not an integer: %r'


class FloatFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that transforms its value into an integer."""

    _type = (float, int)
    _type_error_message = 'not a float: %r'

    def _marshall_from_json_data(self, value):
        """See `SimpleFieldMarshaller`.

        Converts the value to a float.
        """
        return float(
            super(FloatFieldMarshaller, self)._marshall_from_json_data(value))


class BytesFieldMarshaller(SimpleFieldMarshaller):
    """FieldMarshaller for IBytes field."""

    _type = str
    _type_error_message = 'not a string: %r'

    @property
    def representation_name(self):
        """See `IFieldMarshaller`.

        Represent as a link to another resource.
        """
        return "%s_link" % self.field.__name__

    def unmarshall(self, entry, bytestorage):
        """See `IFieldMarshaller`.

        Marshall as a link to the byte storage resource.
        """
        return "%s/%s" % (canonical_url(entry.context), self.field.__name__)

    def _marshall_from_request(self, value):
        """See `SimpleFieldMarshaller`.

        Reads the data from file-like object, and converts non-strings into
        one.
        """
        if safe_hasattr(value, 'seek'):
            value.seek(0)
            value = value.read()
        elif not isinstance(value, basestring):
            value = str(value)
        else:
            # Leave string conversion to _marshall_from_json_data.
            pass
        return super(BytesFieldMarshaller, self)._marshall_from_request(value)

    def _marshall_from_json_data(self, value):
        """See `SimpleFieldMarshaller`.

        Convert all strings to byte strings.
        """
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return super(
            BytesFieldMarshaller, self)._marshall_from_json_data(value)


class TextFieldMarshaller(SimpleFieldMarshaller):
    """FieldMarshaller for IText fields."""

    _type = unicode
    _type_error_message = 'not a unicode string: %r'

    def _marshall_from_request(self, value):
        """See `SimpleFieldMarshaller`.

        Converts the value to unicode.
        """
        value = unicode(value)
        return super(TextFieldMarshaller, self)._marshall_from_request(value)


class TokenizedVocabularyFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that looks up value using a token in a vocabulary."""

    def __init__(self, field, request, vocabulary):
        super(TokenizedVocabularyFieldMarshaller, self).__init__(
            field, request)

    def _marshall_from_json_data(self, value):
        """See `SimpleFieldMarshaller`.

        Looks up the value as a token in the vocabulary.
        """
        try:
            return self.field.vocabulary.getTermByToken(str(value)).value
        except LookupError:
            raise ValueError("%r isn't a valid token" % value)


class DateTimeFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that transforms its value into a datetime object."""

    def _marshall_from_json_data(self, value):
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


class AbstractCollectionFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller for List, Tuple, Set and other AbstractCollections.

    It looks up the marshaller for its value-type, to handle its contained
    elements.
    """
    # The only valid JSON representation is a list.
    _type = list
    _type_error_message = 'not a list: %r'

    def __init__(self, field, request):
        """See `SimpleFieldMarshaller`.

        This also looks for the appropriate marshaller for value_type.
        """
        super(AbstractCollectionFieldMarshaller, self).__init__(
            field, request)
        self.value_marshaller = getMultiAdapter(
            (field.value_type, request), IFieldMarshaller)

    def _marshall_from_json_data(self, value):
        """See `SimpleFieldMarshaller`.

        Marshall every elements of the list using the appropriate
        marshaller.
        """
        value = super(
            AbstractCollectionFieldMarshaller,
            self)._marshall_from_json_data(value)

        # In AbstractCollection subclasses, _type contains the type object,
        # which can be used as a factory.
        return self.field._type(
            self.value_marshaller.marshall_from_json_data(item)
            for item in value)

    def _marshall_from_request(self, value):
        """See `SimpleFieldMarshaller`.

        If the value isn't a list, transform it into a one-element list. That
        allows web client to submit one-element list of strings
        without having to JSON-encode it.

        Additionally, all items in the list are marshalled using the
        appropriate `IFieldMarshaller` for the value_type.
        """
        if not isinstance(value, list):
            value = [value]
        value = [self.value_marshaller.marshall_from_request(item)
                 for item in value]
        return super(
           AbstractCollectionFieldMarshaller,
           self)._marshall_from_request(value)

    def unmarshall(self, entry, value):
        """See `SimpleFieldMarshaller`.

        The collection is unmarshalled into a list and all its items are
        unmarshalled using the appropriate FieldMarshaller.
        """
        return [self.value_marshaller.unmarshall(entry, item)
               for item in value]


class CollectionFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller for collection fields."""

    @property
    def representation_name(self):
        """See `IFieldMarshaller`.

        Make it clear that the value is a link to a collection.
        """
        return "%s_collection_link" % self.field.__name__

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        This returns a link to the scoped collection.
        """
        return "%s/%s" % (canonical_url(entry.context), self.field.__name__)


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

    def _marshall_from_json_data(self, value):
        """Find an item in the vocabulary by title."""
        valid_titles = []
        for item in self.field.vocabulary.items:
            if item.title == value:
                return item
            valid_titles.append(item.title)
        raise ValueError(
            'Invalid value "%s". Acceptable values are: %s' %
            (value, ', '.join(valid_titles)))

    def unmarshall(self, entry, value):
        if value is None:
            return None
        return value.title


class ObjectLookupFieldMarshaller(SimpleFieldMarshaller,
                                  URLDereferencingMixin):
    """A marshaller that turns URLs into data model objects.

    This marshaller can be used with a IChoice field (initialized
    with a vocabulary) or with an IObject field (no vocabulary).
    """

    def __init__(self, field, request, vocabulary=None):
        super(ObjectLookupFieldMarshaller, self).__init__(field, request)
        self.vocabulary = vocabulary

    @property
    def representation_name(self):
        """See `IFieldMarshaller`.

        Make it clear that the value is a link to an object, not an object.
        """
        return "%s_link" % self.field.__name__

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        Represent an object as the URL to that object
        """
        repr_value = None
        if value is not None:
            repr_value = canonical_url(value)
        return repr_value

    def _marshall_from_json_data(self, value):
        """See `IFieldMarshaller`.

        Look up the data model object by URL.
        """
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


class Reference(Object):
    """An Object-like field which doesn't validate all fields of the schema.

    Unlike Object, which does call _validate_fields(self.schema, value) to
    validate all fields, this field will simply call the _validate() method of
    the Field class and then check that the given value provides the specified
    schema.
    """

    def _validate(self, value):
        Field._validate(self, value)
        if not self.schema.providedBy(value):
            raise SchemaNotProvided()
