# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ZCML registration directives for the LAZR webservice framework."""

__metaclass__ = type
__all__ = []


import inspect

from zope.app.component.metaconfigure import handler
from zope.configuration.fields import GlobalObject
from zope.interface import Interface


from canonical.lazr.rest.declarations import (
    LAZR_WEBSERVICE_EXPORTED, generate_collection_adapter,
    generate_entry_adapter, generate_entry_interface)
from canonical.lazr.interfaces.rest import ICollection, IEntry


class IRegisterDirective(Interface):
    """Directive to hook up webservice based on the declarations in a module.
    """
    module = GlobalObject(
        title=u'Module which will be inspected for webservice declarations')


def find_exported_interfaces(module):
    """Find all the interfaces in a module marked for export.

    :return: iterator of interfaces.
    """
    for name, interface in inspect.getmembers(module, inspect.isclass):
        tag = interface.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tag is None:
            continue
        if tag['type'] in ['entry', 'collection']:
            yield interface


def register_webservice(context, module):
    """Generate and register web service adapters.

    All interfaces in the module are inspected, and appropriate interfaces and
    adapters are generated and registered for the one marked for export on the
    web service.
    """
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    for interface in find_exported_interfaces(module):
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
