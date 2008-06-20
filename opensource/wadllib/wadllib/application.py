# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Navigate the resources exposed by a web service.

The wadllib library helps a web client navigate the resources
exposed by a web service. The service defines its resources in a
single WADL file. wadllib parses this file and gives access to the
resources defined inside. The client code can see the capabilities of
a given resource and make the corresponding HTTP requests.

If a request returns a representation of the resource, the client can
bind the string representation to the wadllib Resource object.
"""

__metaclass__ = type

__all__ = [
    'Application',
    'Link',
    'Method',
    'NoBoundRepresentationError',
    'Parameter',
    'RepresentationDefinition',
    'ResponseDefinition',
    'Resource',
    'ResourceType',
    'WADLError',
    ]

import urllib
from urlparse import urlparse
import simplejson
try:
    import xml.etree.cElementTree as ET
except ImportError:
    try:
        import cElementTree as ET
    except ImportError:
        import elementtree.ElementTree as ET
from wadllib._utils import uri

def wadl_tag(tag_name):
    """Scope a tag name with the WADL namespace."""
    return '{http://research.sun.com/wadl/2006/10}' + tag_name


def wadl_xpath(tag_name):
    """Turn a tag name into an XPath path."""
    return './' + wadl_tag(tag_name)


class WADLError(Exception):
    """An exception having to do with the state of the WADL application."""
    pass


class NoBoundRepresentationError(WADLError):
    """An unbound resource was used where wadllib expected a bound resource.

    To obtain the value of a resource's parameter, you first must bind
    the resource to a representation. Otherwise the resource has no
    idea what the value is and doesn't even know if you've given it a
    parameter name that makes sense.
    """


class UnsupportedMediaTypeError(WADLError):
    """A media type was given that's not supported in this context.

    A resource can only be bound to media types it has representations
    of.
    """


class WADLBase:
    """A base class for objects that contain WADL-derived information."""


class HasParamsMixin:
    """A mixin class for objects that have associated Param objects."""

    def _merge_dicts(self, *dicts):
        """Merge any number of dictionaries, some of which may be None."""
        final = {}
        for dict in dicts:
            if dict is not None:
                final.update(dict)
        return final

    def params(self, styles, resource=None):
        """Find subsidiary parameters that have the given styles."""
        if resource is None:
            resource = self.resource
        if resource is None:
            raise ValueError("Could not find any particular resource")
        if self.tag is None:
            return []
        param_tags = self.tag.findall(wadl_xpath('param'))
        if param_tags is None:
            return []
        return [Parameter(resource, param_tag)
                for param_tag in param_tags
                if param_tag.attrib.get('style') in styles]

    def validate_param_values(self, params, param_values,
                              enforce_completeness=True, **kw_param_values):
        """Make sure the given valueset is valid.

        A valueset might be invalid because it contradicts a fixed
        value or (if enforce_completeness is True) because it lacks a
        required value.

        :param params: A list of Param objects.
        :param param_values: A dictionary of parameter values. May include
           paramters whose names are not valid Python identifiers.
        :param enforce_completeness: If True, this method will raise
           an exception when the given value set lacks a value for a
           required parameter.
        :param kw_param_values: A dictionary of parameter values.
        :return: A dictionary of validated parameter values.
        """
        param_values = self._merge_dicts(param_values, kw_param_values)
        validated_values = {}
        for param in params:
            name = param.name
            if param.fixed_value is not None:
                if (param_values.has_key(name)
                    and param_values[name] != param.fixed_value):
                    raise ValueError(("Value '%s' for parameter '%s' "
                                      "conflicts with fixed value '%s'")
                                     % (param_values[name], name,
                                        param.fixed_value))
                param_values[name] = param.fixed_value
            if (param.is_required and not param_values.has_key(name)
                and enforce_completeness):
                raise ValueError("No value for required parameter '%s'"
                                 % name)
            if param_values.has_key(name):
                validated_values[name] = param_values[name]
                del param_values[name]
        if len(param_values) > 0:
            raise ValueError("Unrecognized parameter(s): '%s'"
                             % "', '".join(param_values.keys()))
        return validated_values


class WADLResolvableDefinition(WADLBase):
    """A base class for objects whose definitions may be references."""

    def __init__(self, application):
        """Initialize with a WADL application.

        :param application: A WADLDefinition. Relative links are
            assumed to be relative to this object's URL.
        """
        self._definition = None
        self.application = application

    def resolve_definition(self):
        """Return the definition of this object, wherever it is.

        Resource is a good example. A WADL <resource> tag
        may contain a large number of nested tags describing a
        resource, or it may just contain a 'type' attribute that
        references a <resource_type> which contains those same
        tags. Resource.resolve_definition() will return the original
        Resource object in the first case, and a
        ResourceType object in the second case.
        """
        if self._definition is not None:
            return self._definition
        object_url = self._get_definition_url()
        if object_url is None:
            # The object contains its own definition.
            # XXX leonardr 2008-05-28:
            # This code path is not tested in Launchpad.
            self._definition = self
            return self
        # The object makes reference to some other object. Resolve
        # its URL and return it.
        xml_id = self.application.lookup_xml_id(object_url)
        definition = self._definition_factory(xml_id)
        if definition is None:
            # XXX leonardr 2008-06-
            # This code path is not tested in Launchpad.
            # It requires an invalid WADL file that makes
            # a reference to a nonexistent tag within the
            # same WADL file.
            raise KeyError('No such XML ID: "%s"' % object_url)
        self._definition = definition
        return definition

    def _definition_factory(self, id):
        """Transform an XML ID into a wadllib wrapper object.

        Which kind of object it is depends on the subclass.
        """
        raise NotImplementedError()

    def _get_definition_url(self):
        """Find the URL that identifies an external reference.

        How to do this depends on the subclass.
        """
        raise NotImplementedError()


class Resource(WADLResolvableDefinition):
    """A resource, possibly bound to a representation."""

    def __init__(self, application, url, resource_type,
                 representation=None, media_type=None, _definition=None):
        """
        :param application: A WADLApplication.
        :param url: The URL to this resource.
        :param resource_type: An ElementTree <resource> or <resource_type> tag.
        :param representation: A string representation.
        :param media_type: The media type of the representation.
        :param _definition: A precached value for _definition. Used to
            avoid dereferencing a bound resource definition; instead,
            we reuse the work done when dereferencing the unbound
            resource.
        """
        super(Resource, self).__init__(application)
        self._url = url
        if isinstance(resource_type, basestring):
            # We were passed the URL to a resource type. Look up the
            # type object itself
            self.tag = self.application.get_resource_type(resource_type).tag
        else:
            # We were passed an XML tag that describes a resource or
            # resource type.
            self.tag = resource_type

        self.representation = None
        if representation is not None:
            if media_type == 'application/json':
                self.representation = simplejson.loads(representation)
            else:
                raise UnsupportedMediaTypeError(
                    "This resource doesn't define a representation for "
                    "media type %s" % media_type)
        self.media_type = media_type
        if representation is not None:
            self.representation_definition = (
                self.get_representation_definition(self.media_type))

    @property
    def url(self):
        """Return the URL to this resource."""
        return self._url

    @property
    def id(self):
        """Return the ID of this resource."""
        return self.tag.attrib['id']

    def bind(self, representation, media_type='application/json'):
        """Bind the resource to a representation of that resource.

        :param representation: A string representation
        :param media_type: The media type of the representation.
        :returns: A Resource bound to a particular representation.
        """
        return Resource(self.application, self.url, self.tag,
                        representation, media_type,
                        self._definition)

    def get_representation_definition(self, media_type):
        """Get a description of one of this resource's representations."""
        default_get_response = self.get_method('GET').response
        for representation in default_get_response:
            representation_tag = representation.resolve_definition().tag
            if representation_tag.attrib.get('mediaType') == media_type:
                return representation
        raise UnsupportedMediaTypeError("No definition for representation "
                                        "with media type %s." % media_type)

    def get_method(self, http_method, media_type=None, query_params=None,
                   representation_params=None):
        """Look up one of this resource's methods by HTTP method.

        :param http_method: The HTTP method used to invoke the desired
                            method. Case-insensitive.

        :param media_type: The media type of the representation
                           accepted by the method. Optional.

        :param query_params: The names and values of any fixed query
                             parameters used to distinguish between
                             two methods that use the same HTTP
                             method. Optional.

        :param representation_params: The names and values of any
                             fixed representation parameters used to
                             distinguish between two methods that use
                             the same HTTP method and have the same
                             media type. Optional.

        :returns: A MethodDefinition, or None if there's no definition
                  that fits the given constraints.
        """
        definition = self.resolve_definition().tag
        for method_tag in definition.findall(wadl_xpath('method')):
            name = method_tag.attrib.get('name', '').lower()
            if name == http_method.lower():
                method = Method(self, method_tag)
                if method.is_described_by(media_type, query_params,
                                          representation_params):
                    return method
        return None

    def get_param(self, param_name):
        """Find the value of a parameter within the representation."""
        if self.representation is None:
            raise NoBoundRepresentationError(
                "Resource is not bound to any representation.")
        definition = self.representation_definition.resolve_definition()
        representation_tag = definition.tag
        for param_tag in representation_tag.findall(wadl_xpath('param')):
            if param_tag.attrib.get('name') == param_name:
                return Parameter(self, param_tag)
        return None

    def _definition_factory(self, id):
        """Given an ID, find a ResourceType for that ID."""
        return self.application.resource_types.get(id)

    def _get_definition_url(self):
        """Return the URL that shows where a resource is 'really' defined.

        If a resource's capabilities are defined by reference, the
        <resource> tag's 'type' attribute will contain the URL to the
        <resource_type> that defines them.
        """
        return self.tag.attrib.get('type')


class Method(WADLBase):
    """A wrapper around an XML <method> tag.
    """
    def __init__(self, resource, method_tag):
        """Initialize with a <method> tag.

        :param method_tag: An ElementTree <method> tag.
        """
        self.resource = resource
        self.application = self.resource.application
        self.tag = method_tag

    @property
    def request(self):
        """Return the definition of a request that invokes the WADL method."""
        return RequestDefinition(self, self.tag.find(wadl_xpath('request')))

    @property
    def response(self):
        """Return the definition of the response to the WADL method."""
        return ResponseDefinition(self.resource,
                                  self.tag.find(wadl_xpath('response')))

    @property
    def id(self):
        """The XML ID of the WADL method definition."""
        return self.tag.attrib.get('id')

    @property
    def name(self):
        """The name of the WADL method definition.

        This is also the name of the HTTP method (GET, POST, etc.)
        that should be used to invoke the WADL method.
        """
        return self.tag.attrib.get('name')

    def build_request_url(self,  param_values=None, **kw_param_values):
        """Return the request URL to use to invoke this method."""
        return self.request.build_url(param_values, **kw_param_values)

    def build_representation(self, media_type=None,
                             param_values=None, **kw_param_values):
        """Build a representation to be sent when invoking this method."""
        return self.request.representation(
            media_type, param_values, **kw_param_values)

    def is_described_by(self, media_type=None, query_values=None,
                        representation_values=None):
        """Returns true if this method fits the given constraints.

        :param media_type: The method must accept this media type as a
                           representation.

        :param query_values: These key-value pairs must be acceptable
                           as values for this method's query
                           parameters. This need not be a complete set
                           of parameters acceptable to the method.

        :param representation_values: These key-value pairs must be
                           acceptable as values for this method's
                           representation parameters. Again, this need
                           not be a complete set of parameters
                           acceptable to the method.
        """
        representation = None
        if media_type is not None:
            if self.media_type is not None:
                representation = self.request.get_representation_definition(
                    media_type)
                if representation is None:
                    return False

        if query_values is not None and len(query_values) > 0:
            request = self.request
            if request is None:
                # This method takes no special request
                # parameters, so it can't match.
                return False
            try:
                request.validate_param_values(
                    request.query_params, query_values, False)
            except ValueError:
                return False

        # At this point we know the media type and query values match.
        if (representation_values is None
            or len(representation_values) == 0):
            return True

        if representation is not None:
            return representation.is_described_by(
                representation_values)
        for representation in self.request.representations:
            try:
                representation.validate_param_values(
                    representation.params(self.resource),
                    representation_values, False)
            except ValueError:
                return False
            return True
        return False


class RequestDefinition(WADLBase, HasParamsMixin):
    """A wrapper around the description of the request invoking a method."""
    def __init__(self, method, request_tag):
        """Initialize with a <request> tag.

        :param resource: The resource to which this request can be sent.
        :param request_tag: An ElementTree <request> tag.
        """
        self.method = method
        self.resource = self.method.resource
        self.application = self.resource.application
        self.tag = request_tag

    @property
    def query_params(self):
        """Return the query parameters for this method."""
        return self.params(['query'])

    @property
    def representations(self):
        for definition in self.tag.findall(wadl_xpath('representation')):
            yield RepresentationDefinition(
                self.application, self.resource, definition)

    def representation_definition(self, media_type=None):
        """Return the appropriate representation definition."""
        for representation in self.representations:
            if media_type is None or definition.media_type == media_type:
                return representation
        return None

    def representation(self, media_type=None, param_values=None,
                       **kw_param_values):
        """Build a representation to be sent along with this request."""
        return self.representation_definition(media_type).bind(
            param_values, **kw_param_values)

    def build_url(self, param_values=None, **kw_param_values):
        """Return the request URL to use to invoke this method."""
        validated_values = self.validate_param_values(
            self.query_params, param_values, **kw_param_values)
        url = self.resource.url
        if len(validated_values) > 0:
            if '?' in url:
                append = '&'
            else:
                append = '?'
            url += append + urllib.urlencode(validated_values)
        return url


class ResponseDefinition(WADLBase):
    """A wrapper around the description of a response to a method."""

    # XXX leonardr 2008-05-29 it would be nice to have
    # ResponseDefinitions for POST operations and nonstandard GET
    # operations say what representations and/or status codes you get
    # back. Getting this to work with Launchpad requires work on the
    # Launchpad side.
    def __init__(self, resource, response_tag):
        """Initialize with a <response> tag.

        :param response_tag: An ElementTree <response> tag.
        """
        self.resource = resource
        self.tag = response_tag

    def __iter__(self):
        """Get an iterator over the representation definitions.

        These are the representations returned in response to an
        invocation of this method.
        """
        path = wadl_xpath('representation')
        for representation_tag in self.tag.findall(path):
            yield RepresentationDefinition(
                self.resource.application, self.resource, representation_tag)


class RepresentationDefinition(WADLResolvableDefinition, HasParamsMixin):
    """A definition of the structure of a representation."""

    def __init__(self, application, resource, representation_tag):
        super(RepresentationDefinition, self).__init__(application)
        self.resource = resource
        self.tag = representation_tag

    def params(self, resource):
        return super(RepresentationDefinition, self).params(
            ['query', 'plain'], resource)

    @property
    def media_type(self):
        """The media type of the representation described here."""
        return self.resolve_definition().tag.attrib['mediaType']

    def bind(self, param_values, **kw_param_values):
        """Bind the definition to parameter values, creating a document."""
        validated_values = self.validate_param_values(
            self.resolve_definition().params(self.resource),
            param_values, **kw_param_values)
        if self.media_type == 'application/x-www-form-urlencoded':
            return urllib.urlencode(validated_values)
        elif self.media_type == 'application/json':
            return simplejson.dumps(validated_values)

    def _definition_factory(self, id):
        """Turn a representation ID into a RepresentationDefinition."""
        return self.application.representation_definitions.get(id)

    def _get_definition_url(self):
        """Find the URL containing the representation's 'real' definition.

        If a representation's structure is defined by reference, the
        <representation> tag's 'href' attribute will contain the URL
        to the <representation> that defines the structure.
        """
        return self.tag.attrib.get('href')


class Parameter(WADLBase):
    """One of the parameters of a representation definition."""

    def __init__(self, resource_definition, tag):
        """Initialize with respect to a resource definition.

        :param resource_definition: The resource whose representation
            has this parameter. If the resource is bound to a representation,
            you'll be able to find the value of this parameter in the
            representation.
        :tag: The ElementTree <param> tag for this parameter.
        """
        self.application = resource_definition.application
        self.resource_definition = resource_definition
        self.tag = tag

    @property
    def name(self):
        """The name of this parameter."""
        return self.tag.attrib.get('name')

    @property
    def fixed_value(self):
        """The value to which this parameter is fixed, if any.

        A fixed parameter must be present in invocations of a WADL
        method, and it must have a particular value. This is commonly
        used to designate one parameter as containing the name of the
        server-side operation to be invoked.
        """
        return self.tag.attrib.get('fixed')

    @property
    def is_required(self):
        """Whether or not a value for this parameter is required."""
        return self.tag.attrib.get('required', False).lower() in ['1', 'true']

    def get_value(self):
        """The value of this parameter in the bound representation.

        :raise NoBoundRepresentationError: If this parameter's
        resource is not bound to a representation.
        """
        if self.resource_definition.representation is None:
            raise NoBoundRepresentationError(
                "Resource is not bound to any representation.")
        if self.resource_definition.media_type == 'application/json':
            # XXX leonardr 2008-05-28 A real JSONPath implementation
            # should go here. It should execute tag.attrib['path']
            # against the JSON representation.
            #
            # Right now the implementation assumes the JSON
            # representation is a hash and treats tag.attrib['name'] as a
            # key into the hash.
            if self.tag.attrib['style'] != 'plain':
                raise NotImplementedError(
                    "Don't know how to find value for a parameter of "
                    "type %s." % self.tag.attrib['style'])
            return self.resource_definition.representation[
                self.tag.attrib['name']]

        raise NotImplementedError("Path traversal not implemented for "
                                  "a representation of media type %s."
                                  % self.resource_definition.media_type)

    @property
    def linked_resource(self):
        """Find the type of resource linked to by this parameter.

        This only works for parameters whose WADL definition includes a
        <link> tag that points to a known WADL description.

        :return: A Resource object for the resource at the other end
        of the link.
        """
        link_tag = self.tag.find(wadl_xpath('link'))
        if link_tag is None:
            raise ValueError("This parameter isn't a link to anything.")
        return Link(self, link_tag).resolve_definition()


class Link(WADLResolvableDefinition):
    """A link from one resource to another.

    Calling resolve_definition() on a Link will give you a Resource for the
    type of resource linked to.
    """

    def __init__(self, parameter, link_tag):
        """Initialize the link.

        :param parameter: A Parameter.
        :param link_tag: An ElementTree <link> tag.
        """
        super(Link, self).__init__(parameter.application)
        self.parameter = parameter
        self.tag = link_tag

    def _definition_factory(self, id):
        """Turn a resource type ID into a ResourceType."""
        return Resource(
            self.application, self.parameter.get_value(),
            self.application.resource_types.get(id).tag)

    def _get_definition_url(self):
        """Find the URL containing the definition ."""
        type = self.tag.attrib.get('resource_type')
        if type is None:
            raise WADLError("Parameter is a link, but not to a resource "
                            "with a known WADL description.")
        return type


class ResourceType(WADLBase):
    """A wrapper around an XML <resource_type> tag."""

    def __init__(self, resource_type_tag):
        """Initialize with a <resource_type> tag.

        :param resource_type_tag: An ElementTree <resource_type> tag.
        """
        self.tag = resource_type_tag


class Application(WADLBase):
    """A WADL document made programmatically accessible."""

    def __init__(self, markup_url, markup):
        """Parse WADL and find the most important parts of the document.

        :param markup_url: The URL from which this document was obtained.
        :param markup: The WADL markup itself, or an open filehandle to it.
        """
        self.markup_url = markup_url
        if hasattr(markup, 'read'):
            markup = markup.read()
        self.doc = ET.fromstring(markup)
        self.resources = self.doc.find(wadl_xpath('resources'))
        self.resource_base = self.resources.attrib.get('base')
        self.representation_definitions = {}
        self.resource_types = {}
        for representation in self.doc.findall(wadl_xpath('representation')):
            id = representation.attrib.get('id')
            if id is not None:
                definition = RepresentationDefinition(
                    self, None, representation)
                self.representation_definitions[id] = definition
        for resource_type in self.doc.findall(wadl_xpath('resource_type')):
            id = resource_type.attrib['id']
            self.resource_types[id] = ResourceType(resource_type)

    def get_resource_type(self, resource_type_url):
        """Retrieve a resource type by the URL of its description."""
        xml_id = self.lookup_xml_id(resource_type_url)
        resource_type = self.resource_types.get(xml_id)
        if resource_type is None:
            raise KeyError('No such XML ID: "%s"' % resource_type_url)
        return resource_type

    def lookup_xml_id(self, url):
        """A helper method for locating a part of a WADL document.

        :param url: The URL (with anchor) of the desired part of the
        WADL document.
        :returns: The XML ID corresponding to the anchor.
        """
        parts = urlparse(url)
        all_but_anchor = parts[:5]
        if (all_but_anchor == (('',) * 5)
            or all_but_anchor == urlparse(self.markup_url)[:5]):
            # The URL pointed elsewhere within the same WADL document.
            # Return the anchor within the document.
            return parts[-1]

        # XXX leonardr 2008-05-28:
        # This needs to be implemented eventually for Launchpad so
        # that a script using this client can navigate from a WADL
        # representation of a non-root resource to its definition at
        # the server root.
        raise NotImplementedError("Can't look up definition in another "
                                  "url (%s)" % url)

    def get_resource_by_path(self, path):
        """Locate one of the resources described by this document.

        :param path: The path to the resource.
        """
        # XXX leonardr 2008-05-27 This method only finds top-level
        # resources. That's all we need for Launchpad because we don't
        # define nested resources yet.
        matching = [resource for resource in self.resources
                    if resource.attrib['path'] == path]
        if len(matching) < 1:
            return None
        if len(matching) > 1:
            raise WADLError("More than one resource defined with path %s"
                            % path)
        return Resource(
            self, uri.merge(self.resource_base, path, True), matching[0])
