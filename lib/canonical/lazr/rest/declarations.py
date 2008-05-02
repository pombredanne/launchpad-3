# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Declaration helpers to define a web service."""

__metaclass__ = type
__all__ = [
    'COLLECTION_TYPE',
    'ENTRY_TYPE',
    'FIELD_TYPE',
    'LAZR_WEBSERVICE_EXPORTED',
    'LAZR_WEBSERVICE_NS',
    'OPERATION_TYPES',
    'REQUEST_USER',
    'call_with',
    'collection_default_content',
    'exported',
    'export_as_webservice_collection',
    'export_as_webservice_entry',
    'export_factory_operation',
    'export_operation_as',
    'export_read_operation',
    'export_write_operation',
    'generate_collection_adapter',
    'generate_entry_adapter',
    'generate_entry_interface',
    'generate_operation_adapter',
    'operation_parameters',
    'rename_parameters_as',
    'webservice_error',
    'WebServiceExceptionView',
    ]

import simplejson
import sys

from zope.component import getUtility
from zope.interface import classImplements
from zope.interface.advice import addClassAdvisor
from zope.interface.interface import TAGGED_DATA, InterfaceClass
from zope.interface.interfaces import IInterface, IMethod
from zope.schema import getFields
from zope.schema.interfaces import IField
from zope.security.checker import CheckerPublic

# XXX flacoste 2008-01-25 bug=185958:
# canonical_url and ILaunchBag code should be moved into lazr.
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp import canonical_url

from canonical.lazr.decorates import Passthrough
from canonical.lazr.interface import copy_attribute
from canonical.lazr.interfaces.rest import (
    ICollection, IEntry, IResourceGETOperation, IResourcePOSTOperation)
from canonical.lazr.rest.resource import Collection, Entry
from canonical.lazr.rest.operation import ResourceOperation
from canonical.lazr.interface import copy_attribute
from canonical.lazr.security import protect_schema

LAZR_WEBSERVICE_NS = 'lazr.webservice'
LAZR_WEBSERVICE_EXPORTED = '%s.exported' % LAZR_WEBSERVICE_NS
COLLECTION_TYPE = 'collection'
ENTRY_TYPE = 'entry'
FIELD_TYPE = 'field'
OPERATION_TYPES = ('factory', 'read_operation', 'write_operation')

# Marker to specify that a parameter should contain the request user.
REQUEST_USER = object()


def _check_called_from_interface_def(name):
    """Make sure that the declaration was used from within a class definition.
    """
    # 2 is our caller's caller.
    frame = sys._getframe(2)
    f_locals = frame.f_locals

    # Try to make sure we were called from a class def.
    if (f_locals is frame.f_globals) or ('__module__' not in f_locals):
        raise TypeError(
            "%s can only be used from within an interface definition." % name)


def _check_interface(name, interface):
    """Check that interface provides IInterface or raise a TypeError."""
    if not IInterface.providedBy(interface):
        raise TypeError("%s can only be used on an interface." % name)


def _get_interface_tags():
    """Retrieve the dictionary containing tagged values for the interface.

    This will create it, if it hasn't been defined yet.
    """
    # Our caller is contained within the interface definition.
    f_locals = sys._getframe(2).f_locals
    return f_locals.setdefault(TAGGED_DATA, {})


def export_as_webservice_entry():
    """Mark the content interface as exported on the web service as an entry.
    """
    _check_called_from_interface_def('export_as_webservice_entry()')
    def mark_entry(interface):
        """Class advisor that tags the interface once it is created."""
        _check_interface('export_as_webservice_entry()', interface)
        interface.setTaggedValue(
            LAZR_WEBSERVICE_EXPORTED, dict(type=ENTRY_TYPE))

        # Set the name of the fields that didn't specify it using the
        # 'export_as' parameter in exported(). This must be done here,
        # because the field's __name__ attribute is only set when the
        # interface is created.
        for name, field in getFields(interface).items():
            tag = field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
            if tag is None:
                continue
            if tag['type'] != FIELD_TYPE:
                continue
            if tag['as'] is None:
                tag['as'] = name

        annotate_exported_methods(interface)
        return interface
    addClassAdvisor(mark_entry)


def exported(field, exported_as=None):
    """Mark the field as part of the entry data model.

    :param exported_as: the name under which the field is published in the
        entry. By default, the same name is used.
    :raises TypeError: if called on an object which doesn't provide IField.
    :returns: The field with an added tagged value.
    """
    if not IField.providedBy(field):
        raise TypeError("exported() can only be used on IFields.")
    field.setTaggedValue(
        LAZR_WEBSERVICE_EXPORTED, {'type': FIELD_TYPE, 'as': exported_as})
    return field


def export_as_webservice_collection():
    """Mark the interface as exported on the web service as a collection.

    :raises TypeError: if the interface doesn't have a method decorated with
        @collection_default_content.
    """
    _check_called_from_interface_def('export_as_webservice_collection()')

    # Set the tag at this point, so that future declarations can
    # check it.
    tags = _get_interface_tags()
    tags[LAZR_WEBSERVICE_EXPORTED] = dict(type=COLLECTION_TYPE)

    def mark_collection(interface):
        """Class advisor that tags the interface once it is created."""
        _check_interface('export_as_webservice_collection()', interface)

        tag = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if 'collection_default_content' not in tag:
            raise TypeError(
                "export_as_webservice_collection() is missing a method "
                "tagged with @collection_default_content.")

        annotate_exported_methods(interface)
        return interface

    addClassAdvisor(mark_collection)


def collection_default_content(f):
    """Decorates the method that provides the default values of a collection.

    :raises TypeError: if not called from within an interface exported as a
        collection, or if used more than once in the same interface.
    """
    _check_called_from_interface_def('@collection_default_content')

    tags = _get_interface_tags()
    tag = tags.get(LAZR_WEBSERVICE_EXPORTED)
    if tag is None or tag['type'] != COLLECTION_TYPE:
        raise TypeError(
            "@collection_default_content can only be used from within an "
            "interface exported as a collection.")

    if 'collection_default_content' in tag:
        raise TypeError(
            "only one method should be marked with "
            "@collection_default_content.")

    tag['collection_default_content'] = f.__name__

    return f


def webservice_error(status):
    """Mark the exception with the HTTP status code to use.

    That status code will be used by the view used to handle that kind of
    exceptions on the web service.
    """
    frame = sys._getframe(1)
    f_locals = frame.f_locals

    # Try to make sure we were called from a class def.
    if (f_locals is frame.f_globals) or ('__module__' not in f_locals):
        raise TypeError(
            "webservice_error() can only be used from within an exception "
            "definition.")

    f_locals['__lazr_webservice_error__'] = int(status)


class _method_annotator:
    """Base class for decorators annotating a method.

    The actual method will be wrapped in an IMethod specification once the
    Interface is complete. So we save the annotations in an attribute of the
    method, and the class advisor invoked by export_as_webservice_entry() and
    export_as_webservice_collection() will do the final tagging.
    """

    def __call__(self, method):
        """Annotates the function with the fixed arguments."""
        # Everything in the function dictionary ends up as tagged value
        # in the interface method specification.
        annotations = method.__dict__.setdefault(LAZR_WEBSERVICE_EXPORTED, {})
        self.annotate_method(method, annotations)
        return method

    def annotate_method(self, method, annotations):
        """Add annotations for method.

        This method must be implemented by subclasses.

        :param f: the method being annotated.
        :param annotations: the dict containing the method annotations.

        The annotations will copied to the lazr.webservice.exported tag
        by a class advisor.
        """
        raise NotImplemented


def annotate_exported_methods(interface):
    """Sets the 'lazr.webservice.exported' tag on exported method."""

    for name, method in interface.namesAndDescriptions(True):
        if not IMethod.providedBy(method):
            continue
        annotations = method.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if annotations is None:
            continue

        # Method is exported under its own name by default.
        if 'as' not in annotations:
            annotations['as'] = method.__name__

        # It's possible that call_with or operation_parameters weren't used.
        annotations.setdefault('call_with', {})
        annotations.setdefault('params', {})

        # Make sure that all parameters exists and that we miss none.
        info = method.getSignatureInfo()
        defined_params = set(info['optional'])
        defined_params.update(info['required'])
        exported_params = set(annotations['params'])
        exported_params.update(annotations['call_with'])
        undefined_params = exported_params.difference(defined_params)
        if undefined_params and info['kwargs'] is None:
            raise TypeError(
                'method "%s" doesn\'t have the following exported '
                'parameters: %s.' % (
                    method.__name__, ", ".join(sorted(undefined_params))))
        missing_params = set(
            info['required']).difference(exported_params)
        if missing_params:
            raise TypeError(
                'method "%s" needs more parameters definitions to be '
                'exported: %s' % (
                    method.__name__, ", ".join(sorted(missing_params))))


class call_with(_method_annotator):
    """Decorator specifying fixed parameters for exported methods."""

    def __init__(self, **params):
        """Specify fixed values for parameters."""
        _check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.params = params

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        annotations['call_with'] = self.params


class export_operation_as(_method_annotator):
    """Decorator specifying the name to export the method as."""

    def __init__(self, name):
        _check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.name = name

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        annotations['as'] = self.name


class rename_parameters_as(_method_annotator):
    """Decorator specifying the name to export the method parameters as."""

    def __init__(self, **params):
        """params is of the form method_parameter_name=webservice_name."""
        _check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.params = params

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        param_defs = annotations.get('params')
        if param_defs is None:
            raise TypeError(
                '"%s" isn\'t exported on the webservice.' % method.__name__)
        for name, export_as in self.params.items():
            if name not in param_defs:
                raise TypeError(
                    'rename_parameters_as(): no "%s" parameter is exported.' %
                        name)
            param_defs[name].__name__ = export_as


class operation_parameters(_method_annotator):
    """Specify the parameters taken by the exported operation.

    The decorator takes a list of `IField` describing the parameters. The name
    of the underlying method parameter is taken from the argument name.
    """
    def __init__(self, **params):
        """params is of the form method_parameter_name=Field()."""
        _check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.params = params

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        # It's possible that another decorator already created the params
        # annotation.
        params = annotations.setdefault('params', {})
        for name, param in self.params.items():
            if not IField.providedBy(param):
                raise TypeError(
                    'export definition of "%s" in method "%s" must '
                    'provide IField: %r' % (name, method.__name__, param))
            if name in params:
                raise TypeError(
                    "'%s' parameter is already defined." % name)

            # By default, parameters are exported under their own name.
            param.__name__ = name

            params[name] = param


class _export_operation(_method_annotator):
    """Basic implementation for the webservice operation method decorators."""

    # Should be overriden in subclasses with the string to use as 'type'.
    type = None

    def __init__(self):
        _check_called_from_interface_def('%s()' % self.__class__.__name__)

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        annotations['type'] = self.type


class export_factory_operation(_export_operation):
    """Decorator marking a method as being a factory on the webservice."""
    type = 'factory'

    def __init__(self, interface, field_names):
        """Creates a factory decorator.

        :param interface: The interface where fields specified in field_names
            are looked-up.
        :param field_names: The names of the fields in the schema that
            are used as parameters by this factory.
        """
        _check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.interface = interface
        self.params = {}
        for name in field_names:
            field = interface.get(name)
            if field is None:
                raise TypeError("%s doesn't define '%s'." % (
                                interface.__name__, name))
            if not IField.providedBy(field):
                raise TypeError("%s.%s doesn't provide IField." % (
                                interface.__name__, name))
            self.params[name] = copy_attribute(field)

    def annotate_method(self, method, annotations):
        """See `_method_annotator`."""
        super(export_factory_operation, self).annotate_method(
            method, annotations)
        annotations['creates'] = self.interface
        annotations['params'] = self.params


class export_read_operation(_export_operation):
    """Decorator marking a method for export as a read operation."""
    type = 'read_operation'


class export_write_operation(_export_operation):
    """Decorator marking a method for export as a write operation."""
    type = "write_operation"


def _check_tagged_interface(interface, type):
    """Make sure that the interface is exported under the proper type."""
    if not isinstance(interface, InterfaceClass):
        raise TypeError('not an interface.')

    tag = interface.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    if tag is None:
        raise TypeError(
            "'%s' isn't tagged for webservice export." % interface.__name__)
    elif tag['type'] != type:
        art = 'a'
        if type == 'entry':
            art = 'an'
        raise TypeError(
            "'%s' isn't exported as %s %s." % (interface.__name__, art, type))


def generate_entry_interface(interface):
    """Create an IEntry subinterface based on the tags in interface."""

    _check_tagged_interface(interface, 'entry')
    attrs = {}
    for name, field in getFields(interface).items():
        tag = field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None:
            continue
        attrs[tag['as']] = copy_attribute(field)

    return InterfaceClass(
        "%sEntry" % interface.__name__, bases=(IEntry, ), attrs=attrs,
        __doc__=interface.__doc__, __module__=interface.__module__)


def generate_entry_adapter(content_interface, webservice_interface):
    """Create a class adapting from content_interface to webservice_interface.
    """
    _check_tagged_interface(content_interface, 'entry')

    if not isinstance(webservice_interface, InterfaceClass):
        raise TypeError('webservice_interface is not an interface.')

    class_dict = {'schema': webservice_interface}
    for name, field in getFields(content_interface).items():
        tag = field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None:
            continue
        class_dict[tag['as']] = Passthrough(name, 'context')

    classname = "%sAdapter" % webservice_interface.__name__[1:]
    factory = type(classname, bases=(Entry,), dict=class_dict)

    classImplements(factory, webservice_interface)

    protect_schema(
        factory, webservice_interface, write_permission=CheckerPublic)
    return factory


def generate_collection_adapter(interface):
    """Create a class adapting from interface to ICollection."""
    _check_tagged_interface(interface, 'collection')

    tag = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    method_name = tag['collection_default_content']
    class_dict = {
        'find': lambda self: (getattr(self.context, method_name)()),
        }
    classname = "%sCollectionAdapter" % interface.__name__[1:]
    factory = type(classname, bases=(Collection,), dict=class_dict)

    protect_schema(factory, ICollection)
    return factory


class WebServiceExceptionView:
    """Generic view handling exceptions on the web service."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Generate the HTTP response describing the exception."""
        response = self.request.response
        response.setStatus(self.context.__lazr_webservice_error__)
        response.setHeader('Content-Type', 'text/plain')

        return str(self.context)


class BaseResourceOperationAdapter(ResourceOperation):
    """Base class for generated operation adapters."""

    def _getMethodParameters(self, kwargs):
        """Return the method parameters.

        This takes the validated parameters list and handle any possible
        renames, and adds the parameters fixed using @call_with.

        :returns: a dictionary.
        """
        # Handle renames.
        renames = dict(
            (param_def.__name__, orig_name)
            for orig_name, param_def in self._export_info['params'].items()
            if param_def.__name__ != orig_name)
        params = {}
        for name, value in kwargs.items():
            name = renames.get(name, name)
            params[name] = value

        # Handle fixed parameters.
        for name, value in self._export_info['call_with'].items():
            if value is REQUEST_USER:
                value = getUtility(ILaunchBag).user
            params[name] = value
        return params

    def call(self, **kwargs):
        """See `ResourceOperation`."""
        params = self._getMethodParameters(kwargs)
        result = getattr(self.context, self._method_name)(**params)

        # The webservice assumes that the request is complete when the
        # operation returns a string. So we take care of marshalling the
        # result to json.
        if isinstance(result, basestring):
            response = self.request.response
            response.setHeader('Content-Type', 'application/json')
            return simplejson.dumps(result)
        else:
            # Use the default webservice encoding.
            return result


class BaseFactoryResourceOperationAdapter(BaseResourceOperationAdapter):
    """Base adapter class for factory operations."""

    def call(self, **kwargs):
        """See `ResourceOperation`.

        Factory uses the 201 status code on success and sets the Location
        header to the URL to the created object.
        """
        params = self._getMethodParameters(kwargs)
        result = getattr(self.context, self._method_name)(**params)
        response = self.request.response
        response.setStatus(201)
        response.setHeader('Location', canonical_url(result))
        return u''


def generate_operation_adapter(method):
    """Create an IResourceOperation adapter for the exported method."""

    if not IMethod.providedBy(method):
        raise TypeError("%r doesn't provide IMethod." % method)
    tag = method.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    if tag is None:
        raise TypeError(
            "'%s' isn't tagged for webservice export." % method.__name__)

    bases = (BaseResourceOperationAdapter, )
    if tag['type'] == 'read_operation':
        prefix = 'GET'
        provides = IResourceGETOperation
    elif tag['type'] in ('factory', 'write_operation'):
        provides = IResourcePOSTOperation
        prefix = 'POST'
        if tag['type'] == 'factory':
            bases = (BaseFactoryResourceOperationAdapter,)
    else:
        raise AssertionError('Unknown method export type: %s' % tag['type'])

    name = '%s_%s_%s' % (prefix, method.interface.__name__, tag['as'])
    class_dict = {'params' : tuple(tag['params'].values()),
             '_export_info': tag,
             '_method_name': method.__name__}
    factory = type(name, bases, class_dict)
    classImplements(factory, provides)
    protect_schema(factory, provides)

    return factory

