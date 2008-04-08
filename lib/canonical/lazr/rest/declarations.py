# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Declaration helpers to define a web service."""

__metaclass__ = type
__all__ = [
    'ENTRY_TYPE',
    'FIELD_TYPE',
    'LAZR_WEBSERVICE_EXPORTED',
    'export_entry',
    'export_field',
    ]

import sys

from zope.interface.interfaces import IInterface
from zope.interface.advice import addClassAdvisor
from zope.schema.interfaces import IField

LAZR_WEBSERVICE_EXPORTED = 'lazr.webservice.exported'
ENTRY_TYPE = 'entry'
FIELD_TYPE = 'field'


def export_entry():
    """Mark the content interface as exported on the web service as an entry.
    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def.
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError(
            "export_entry() can only be used from within an interface "
            "definition.")
    def tagInterface(interface):
        """Class advisor that tags the interface once its created."""
        if not IInterface.providedBy(interface):
            raise TypeError(
                "export_entry() can only be used on an interface.")
        interface.setTaggedValue(
            LAZR_WEBSERVICE_EXPORTED, dict(type=ENTRY_TYPE))

        # Update the field tags. Set the names of those that don't have an
        # exported name to their default name.
        for name in interface.names(False):
            tag = interface[name].queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
            if tag is None:
                continue
            if tag['type'] != FIELD_TYPE:
                continue
            if tag['as'] is None:
                tag['as'] = name

        return interface
    addClassAdvisor(tagInterface)


def export_field(field, as=None):
    """Mark the field as part of the entry data model.

    :param as: the name under which the field is published in the entry. By
    default, the same name is used.
    """
    if not IField.providedBy(field):
        raise TypeError("export_field() can only be used on IFields.")
    field.setTaggedValue(
        LAZR_WEBSERVICE_EXPORTED, dict(type=FIELD_TYPE, as=as))
