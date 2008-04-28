# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ZCML registration directives for the LAZR webservice framework."""

__metaclass__ = type
__all__ = []


import inspect

from zope.app.component.metaconfigure import handler
from zope.configuration.fields import GlobalObject
from zope.interface import Interface
from zope.interface.interfaces import IInterface


from canonical.lazr.rest.declarations import (
    LAZR_WEBSERVICE_EXPORTED, OPERATION_TYPES, generate_collection_adapter,
    generate_entry_adapter, generate_entry_interface,
    generate_operation_adapter, WebServiceExceptionView)
from canonical.lazr.interfaces.rest import (
    ICollection, IEntry, IResourceGETOperation, IResourcePOSTOperation,
    WebServiceLayer)


class IRegisterDirective(Interface):
    """Directive to hook up webservice based on the declarations in a module.
    """
    module = GlobalObject(
        title=u'Module which will be inspected for webservice declarations')


def find_exported_interfaces(module):
    """Find all the interfaces in a module marked for export.

    It also includes exceptions that represents errors on the webservice.

    :return: iterator of interfaces.
    """
    for name, interface in inspect.getmembers(module, inspect.isclass):
        if issubclass(interface, Exception):
            if getattr(interface, '__lazr_webservice_error__', None) is None:
                continue
            yield interface

        if not IInterface.providedBy(interface):
            continue
        tag = interface.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None:
            continue
        if tag['type'] in ['entry', 'collection']:
            yield interface


def register_webservice(context, module):
    """Generate and register web service adapters.

    All interfaces in the module are inspected, and appropriate interfaces and
    adapters are generated and registered for the ones marked for export on
    the web service.
    """
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    for interface in find_exported_interfaces(module):
        if issubclass(interface, Exception):
            register_exception_view(context, interface)
            continue

        tag = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag['type'] == 'entry':
            web_interface = generate_entry_interface(interface)
            factory = generate_entry_adapter(interface, web_interface)
            provides = IEntry
        elif tag['type'] == 'collection':
            factory = generate_collection_adapter(interface)
            provides = ICollection
        else:
            raise AssertionError('Unknown export type: %s' % tag['type'])
        context.action(
            discriminator=('adapter', interface, provides, ''),
            callable=handler,
            args=('provideAdapter',
                  (interface, ), provides, '', factory, context.info),
            )
        register_webservice_operations(context, interface)


def register_webservice_operations(context, interface):
    """Create and register adapters for all exported methods."""

    for name, method in interface.namesAndDescriptions(True):
        tag = method.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None or tag['type'] not in OPERATION_TYPES:
            continue
        if tag['type'] == 'read_operation':
            provides = IResourceGETOperation
        elif tag['type'] in ['factory', 'write_operation']:
            provides = IResourcePOSTOperation
        else:
            raise AssertionError('Unknown operation type: %s' % tag['type'])
        factory = generate_operation_adapter(method)
        context.action(
            discriminator=(
                'adapter', (interface, WebServiceLayer), provides, tag['as']),
            callable=handler,
            args=('provideAdapter',
                  (interface, WebServiceLayer), provides, tag['as'], factory,
                  context.info),
            )


def register_exception_view(context, exception):
    """Register WebServiceExceptionView to handle exception on the webservice.
    """
    context.action(
        discriminator=(
            'view', exception, '+index', WebServiceLayer, WebServiceLayer),
        callable=handler,
        args=('provideAdapter',
              (exception, WebServiceLayer), Interface, '+index',
              WebServiceExceptionView, context.info),
        )


