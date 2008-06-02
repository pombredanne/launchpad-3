#!/usr/bin/python
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The wadllib library helps a web client navigate the resources
exposed by a web service. The service defines its resources in a
single WADL file, or in many WADL files that reference each other
(currently only a single-file solution is supported). wadllib parses a
WADL file and gives access to the resources defined inside. The client
code can see the capabilities of a given resource and make the
corresponding HTTP requests.

If a request returns a representation of the resource, the client can
bind the string representation to the wadllib Resource object.
"""

__all__ = [
    'Application',
    'Link',
    'Method',
    'Parameter',
    'RepresentationDefinition',
    'ResponseDefinition',
    'Resource',
    'ResourceType',
    ]

import simplejson
import xml.etree.cElementTree as ET

class WADLBase:
    """A base class for objects that contain WADL-derived information."""

    def _url_path_join(self, url, path):
        """Tack an extra path variable onto a URL."""
        if url[-1] == '/':
            return url + path
        return url + '/' + path

    def _path(self, tag_name):
        """Turn a tag name into an XPath path."""
        return './{http://research.sun.com/wadl/2006/10}' + tag_name


class WADLMayBeReference(WADLBase):
    """A base class for objects whose definitions may be references."""

    def __init__(self, application):
        """Initialize with a WADL application.

        :param application: A WADLDefinition. Relative links are
            assumed to be relative to this object's URL.
        """
        self._definition = None
        self.wadl_url = application.markup_url

    def dereference(self):
        """Return the definition of this object, wherever it is.

        Resource is a good example. A WADL <resource> tag
        may contain a large number of nested tags describing a
        resource, or it may just contain a 'type' attribute that
        references a <resource_type> which contains those same
        tags. Resource.dereference() will return the original
        Resource object in the first case, and a
        ResourceType object in the second case.
        """
        if self._definition is not None:
            return self._definition
        object_url = self._getObjectURL()
        if object_url is None:
            # The object contains its own definition.
            # XXX leonardr 2008-05-28:
            # This code path is not tested in Launchpad.
            self._definition = self
            return self
        # The object makes reference to some other object. Resolve
        # its URL and return it.
        if (object_url.startswith('#')
            or object_url.startswith(self.wadl_url + '#')):
            # The reference is defined in the same document as the
            # originator. Look it up.
            id = object_url[object_url.index('#')+1:]
            description = self._objectFactory(id)
            if description is None:
                raise KeyError('No such XML ID: "%s"' % object_url)
            self._definition = description
            return description

        # XXX leonardr 2008-05-28:
        # This needs to be implemented eventually for Launchpad so
        # that a script using this client can navigate from a WADL
        # representation of a non-root resource to its definition at
        # the server root.
        raise NotImplementedError("Can't look up definition in another "
                                  "url (%s)" % resource_type_url)

    def _objectFactory(self, id):
        """Transform an XML ID into a wadllib wrapper object.

        Which kind of object it is depends on the subclass.
        """
        raise NotImplementedError()

    def _getObjectURL(self):
        """Find the URL that identifies an external reference.

        How to do this depends on the subclass.
        """
        raise NotImplementedError()


class Resource(WADLMayBeReference):
    """A resource, possibly bound to a representation."""

    def __init__(self, application, url, resource_tag, representation=None,
                 media_type=None, _definition=None):
        """
        :param application: A WADLDefinition.
        :param url: The URL to this resource.
        :param resource_tag: An ElementTree <resource> or <resource_type> tag.
        :param representation: A string representation.
        :param media_type: The media type of the representation.
        :param _definition: A precached value for _definition. Used to
            avoid dereferencing a bound resource definition; instead,
            we reuse the work done when dereferencing the unbound
            resource.
        """
        WADLMayBeReference.__init__(self, application)
        self.application = application
        self._url = url
        self.tag = resource_tag
        self.representation = None
        if representation != None:
            if media_type == 'application/json':
                self.representation = simplejson.loads(representation)
            else:
                raise ValueError("I don't know how to handle a "
                                 "representation of media type "
                                 "%s" % media_type)
        self.media_type = media_type
        if representation is not None:
            self.representation_definition = self.getRepresentationDefinition(
                self.media_type)

    def url(self):
        """Return the URL to this resource."""
        return self._url

    def bind(self, representation, media_type='application/json'):
        """Bind the resource to a representation of that resource.

        :param representation: A string representation
        :param media_type: The media type of the representation.
        :param return: A Resource bound to a particular
                       representation.
        """
        return Resource(self.application, self.url(), self.tag,
                        representation, media_type,
                        self._definition)

    def representationDefinitionIter(self):
        """Get an iterator over the representation definitions.

        These are the representations returned in response to a
        standard GET request.
        """
        method_tag = self.findMethod('GET')
        response = method_tag.response()
        for representation in response.representationDefinitionIter():
            yield representation

    def getRepresentationDefinition(self, mediaType):
        """Get a description of one of this resource's representations."""
        for representation in self.representationDefinitionIter():
            representation_tag = representation.dereference().tag
            if representation_tag.attrib.get('mediaType') == self.media_type:
                return representation
        raise ValueError("No definition for representation with "
                         "media type %s" % media_type)

    def findMethod(self, http_method, fixed_params=None):
        """Look up one of this resource's methods by HTTP method.

        :param http_method: The HTTP method used to invoke the desired
                            method.

        :param fixed_params: The names and values of any fixed
                             parameters used to distinguish between
                             two methods that use the same HTTP
                             method.

        :param return: A MethodDefinition
        """
        definition = self.dereference().tag
        for method_tag in definition.findall(self._path('method')):
            if method_tag.attrib.get('name').lower() == http_method.lower():
                if fixed_params is not None:
                    request = method_tag.find(self._path('request'))
                    if request is not None:
                        matched_params = {}
                        for name, fixed_value in fixed_params.items():
                            for param in request.findall(self._path('param')):
                                if (param.attrib['name'] == name
                                    and param.attrib['fixed'] == fixed_value):
                                    matched_params[name] = param
                        if len(matched_params) != len(fixed_params.keys()):
                            # Skip to the next method
                            continue
                return Method(self.application, method_tag)
        return None

    def findParam(self, param_name):
        """Find the value of a parameter within the representation."""
        if self.representation is None:
            raise ValueError("Resource is not bound to any representation.")
        representation_tag = self.representation_definition.dereference().tag
        for param_tag in representation_tag.findall(self._path('param')):
            if param_tag.attrib.get('name') == param_name:
                return Parameter(self, param_tag)
        return None

    def _objectFactory(self, id):
        """Given an ID, find a ResourceType for that ID."""
        return self.application.resource_types.get(id)

    def _getObjectURL(self):
        """Return the URL that shows where a resource is 'really' defined.

        If a resource's capabilities are defined by reference, the
        <resource> tag's 'type' attribute will contain the URL to the
        <resource_type> that defines them.
        """
        return self.tag.attrib.get('type')


class Method(WADLBase):
    """A wrapper around an XML <method> tag.
    """
    def __init__(self, application, method_tag):
        """Initialize with a <method> tag.

        :param method_tag: An ElementTree <method> tag.
        """
        self.application = application
        self.tag = method_tag
        self.attrib = self.tag.attrib

    def response(self):
        """Return the definition of the response to this method."""
        return ResponseDefinition(self.application,
                                  self.tag.find(self._path('response')))


class ResponseDefinition(WADLBase):
    """A wrapper around the description of a response to a method."""

    # XXX leonardr 2008-05-29 it would be nice to have
    # ResponseDefinitions for POST operations and nonstandard GET
    # operations say what representations and/or status codes you get
    # back. Getting this to work with Launchpad requires work on the
    # Launchpad side.
    def __init__(self, application, response_tag):
        """Initialize with a <response> tag.

        :param response_tag: An ElementTree <response> tag.
        """
        self.application = application
        self.tag = response_tag

    def representationDefinitionIter(self):
        """Get an iterator over the representation definitions.

        These are the representations returned in response to an
        invocation of this method.
        """
        path = self._path('representation')
        for representation_tag in self.tag.findall(path):
            yield RepresentationDefinition(self.application,
                                           representation_tag)


class RepresentationDefinition(WADLMayBeReference):
    """A definition of the structure of a representation."""

    def __init__(self, application, representation_tag):
        WADLMayBeReference.__init__(self, application)
        self.application = application
        self.tag = representation_tag

    def _objectFactory(self, id):
        """Turn a representation ID into a RepresentationDefinition."""
        return self.application.representation_definitions.get(id)

    def _getObjectURL(self):
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

    def value(self):
        """The value of this parameter in the bound representation.

        Raises an error if this parameter's resource is not bound to a
        representation.
        """
        if self.resource_definition.representation is None:
            raise ValueError("Resource is not bound to any representation.")
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

        raise NotImplementedError("Don't know how to do path traversal for "
                                  "a representation of media type %s."
                                  % self.resource_definition.media_type)

    def linked_resource(self):
        """Find the type of resource linked to by this parameter.

        This only works for parameters whose WADL definition includes a
        <link> tag that points to a known WADL description.
        """
        link_tag = self.tag.find(self._path('link'))
        if link_tag is None:
            raise ValueError("This parameter isn't a link to anything.")
        return Link(self, link_tag).dereference()


class Link(WADLMayBeReference):
    """A link from one resource to another.

    Calling declaration() on a Link will give you a Resource for the
    type of resource linked to.
    """

    def __init__(self, parameter, link_tag):
        """Initialize the link.

        :param parameter: A Parameter.
        :param link_tag: An ElementTree <link> tag.
        """
        self.application = parameter.application
        WADLMayBeReference.__init__(self, self.application)
        self.parameter = parameter
        self.tag = link_tag

    def _objectFactory(self, id):
        """Turn a resource type ID into a ResourceType."""
        return Resource(
            self.application, self.parameter.value(),
            self.application.resource_types.get(id).tag)

    def _getObjectURL(self):
        """Find the URL containing the definition ."""
        type = self.tag.attrib.get('resource_type')
        if type is None:
            raise ValueError("Parameter is a link, but not to a resource "
                             "with a known WADL description.")
        return type


class ResourceType(WADLBase):
    """A wrapper around an XML <resource_type> tag."""

    def __init__(self, resource_type_tag):
        """Initialize with a <resource_type> tag.

        :param resource_type_tag: An ElementTree <resource_type> tag.
        """
        self.tag = resource_type_tag

    def id(self):
        return self.tag.attr.get('id')


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
        self.resources = self.doc.find(self._path('resources'))
        self.resource_base = self.resources.attrib.get('base')
        self.representation_definitions = {}
        self.resource_types = {}
        for representation in self.doc.findall(self._path('representation')):
            id = representation.attrib.get('id')
            if id is not None:
                definition = RepresentationDefinition(self, representation)
                self.representation_definitions[id] = definition
        for resource_type in self.doc.findall(self._path('resource_type')):
            id = resource_type.attrib.get('id')
            if id is not None:
                self.resource_types[id] = ResourceType(resource_type)

    def findResourceByPath(self, path):
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
        return Resource(
            self, self._url_path_join(self.resource_base, path), matching[0])
