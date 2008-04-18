# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Declaration helpers to define a web service."""

__metaclass__ = type
__all__ = [
    'COLLECTION_TYPE',
    'ENTRY_TYPE',
    'FIELD_TYPE',
    'LAZR_WEBSERVICE_EXPORTED',
    'LAZR_WEBSERVICE_NS',
    'REQUEST_USER',
    'call_with',
    'collection_default_content',
    'export_as',
    'export_collection',
    'export_entry',
    'export_factory_operation',
    'export_field',
    'export_read_operation',
    'export_write_operation',
    'generate_collection_adapter',
    'generate_entry_adapter',
    'generate_entry_interface',
    ]

import sys

from zope.interface import classImplements
from zope.interface.advice import addClassAdvisor
from zope.interface.interface import TAGGED_DATA, InterfaceClass
from zope.interface.interfaces import IInterface
from zope.schema import getFields
from zope.schema.interfaces import IField
from zope.security.checker import CheckerPublic

from canonical.lazr.decorates import Passthrough
from canonical.lazr.interface import copy_attribute
from canonical.lazr.interfaces.rest import ICollection, IEntry
from canonical.lazr.rest.resource import Collection, Entry
from canonical.lazr.security import protect_schema

LAZR_WEBSERVICE_NS = 'lazr.webservice'
LAZR_WEBSERVICE_EXPORTED = '%s.exported' % LAZR_WEBSERVICE_NS
COLLECTION_TYPE = 'collection'
ENTRY_TYPE = 'entry'
FIELD_TYPE = 'field'

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


def export_entry():
    """Mark the content interface as exported on the web service as an entry.
    """
    _check_called_from_interface_def('export_entry()')
    def mark_entry(interface):
        """Class advisor that tags the interface once it is created."""
        _check_interface('export_entry()', interface)
        interface.setTaggedValue(
            LAZR_WEBSERVICE_EXPORTED, dict(type=ENTRY_TYPE))

        # Set the name of the fields that didn't specify it using the 'as'
        # parameter in export_field. This must be done here, because the
        # field's __name__ attribute is only set when the interface is
        # created.
        for name in interface.names(False):
            tag = interface[name].queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
            if tag is None:
                continue
            if tag['type'] != FIELD_TYPE:
                continue
            if tag['as'] is None:
                tag['as'] = name

        annotate_exported_methods(interface)
        return interface
    addClassAdvisor(mark_entry)


def export_field(field, as=None):
    """Mark the field as part of the entry data model.

    :param as: the name under which the field is published in the entry. By
        default, the same name is used.
    :raises TypeError: if called on an object which doesn't provide IField.
    """
    if not IField.providedBy(field):
        raise TypeError("export_field() can only be used on IFields.")
    field.setTaggedValue(
        LAZR_WEBSERVICE_EXPORTED, dict(type=FIELD_TYPE, as=as))


def export_collection():
    """Mark the interface as exported on the web service as a collection.

    :raises TypeError: if the interface doesn't have a method decorated with
        @collection_default_content.
    """
    _check_called_from_interface_def('export_collection()')

    # Set the tag at this point, so that future declarations can
    # check it.
    tags = _get_interface_tags()
    tags[LAZR_WEBSERVICE_EXPORTED] = dict(type=COLLECTION_TYPE)

    def mark_collection(interface):
        """Class advisor that tags the interface once it is created."""
        _check_interface('export_collection()', interface)

        tag = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if 'collection_default_content' not in tag:
            raise TypeError(
                "export_collection() is missing a method tagged with "
                "@collection_default_content.")

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


class _method_annotator:
    """Base class for decorator annotating a method.

    The actual method will be wrapped in IMethod specification, only once the
    Interface is complete. So we save the annotations in a tag value of the
    interface, and the class advisor invoked by export_entry() and
    export_collection(), will do the final tagging.
    """

    def __init__(self, **params):
        """All operation specify their parameters using schema fields."""
        #_check_called_from_interface_def('%s()' % self.__class__.__name__)
        self.params = params

    def __call__(self, f):
        """Annotates the function with the fixed arguments."""
        tags = _get_interface_tags()
        annotations = tags.setdefault(
            'lazr.webservice.exported_methods_annotations', {})
        method_annotations = annotations.setdefault(f.__name__, {})
        self.annotate_method(f, method_annotations)
        return f

    def annotate_method(self, f, annotations):
        """Add annotations for method f.

        This method must be implemented by subclasses.

        :param f: the method being annotated.
        :param annotations: the dict containing the method annotations.

        The annotations will copied to the lazr.webservice.exported tag
        by a class advisor.
        """
        raise NotImplemented


def annotate_exported_methods(interface):
    """Sets the 'lazr.webservice.exported' tag on exported method."""

    exported_methods = interface.queryTaggedValue(
        'lazr.webservice.exported_methods_annotations')
    if exported_methods is None:
        return

    for name, annotations in exported_methods.items():
        method = interface.get(name)
        # Method is exported under its own name by default.
        if 'as' not in annotations:
            annotations['as'] = method.__name__
        annotations.setdefault('call_with', {})

        # Set the __name__ attribute on all parameters.
        for name, param in annotations['params'].items():
            if not param.__name__:
                param.__name__ = name
        method.setTaggedValue(LAZR_WEBSERVICE_EXPORTED, annotations)


class call_with(_method_annotator):
    """Decorator specifying fixed parameters for exported methods."""

    def annotate_method(self, f, annotations):
        """See `_method_annotator`."""
        annotations['call_with'] = self.params


class export_as(_method_annotator):
    """Decorator specifying the name to export the method as."""

    def __init__(self, name):
        # pylint: disable-msg=W0231
        #_check_called_from_interface_def('export_as()')
        self.name = name

    def annotate_method(self, f, annotations):
        """See `_method_annotator`."""
        annotations['as'] = self.name


class _export_operation(_method_annotator):
    """Basic implementation for the webservice operation method decorators."""

    # Should be overriden in subclasses with the string to use as 'type'.
    type = None

    def annotate_method(self, f, annotations):
        """See `_method_annotator`."""
        annotations['type'] = self.type
        annotations['params'] = self.params


class export_factory_operation(_export_operation):
    """Decorator marking a method as being a factory on the webservice."""
    type = 'factory'


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

    cdict = {'schema': webservice_interface}
    for name, field in getFields(content_interface).items():
        tag = field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None:
            continue
        cdict[tag['as']] = Passthrough(name, 'context')

    classname = "%sAdapter" % webservice_interface.__name__[1:]
    factory = type(classname, bases=(Entry,), dict=cdict)

    classImplements(factory, webservice_interface)

    protect_schema(
        factory, webservice_interface, write_permission=CheckerPublic)
    return factory


def generate_collection_adapter(interface):
    """Create a class adapting from interface to ICollection."""
    _check_tagged_interface(interface, 'collection')

    tag = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    method_name = tag['collection_default_content']
    cdict = {
        'find': lambda self: (getattr(self.context, method_name)()),
        }
    classname = "%sCollectionAdapter" % interface.__name__[1:]
    factory = type(classname, bases=(Collection,), dict=cdict)

    protect_schema(factory, ICollection)
    return factory
