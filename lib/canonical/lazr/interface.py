# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers for working with Zope interface."""

__metaclass__ = type
__all__ = [
        'copy_attribute',
        'copy_field',
        'use_template'
        ]

import sys
from copy import copy

from zope.interface.interfaces import IAttribute
from zope.schema import Field
from zope.schema.interfaces import IField


def use_template(template, include=None, exclude=None):
    """Copy some field definitions from an interface into this one."""
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def.
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError(
            "use_template() can only be used from within a class definition.")

    if include and exclude:
        raise ValueError(
            "you cannot use 'include' and 'exclude' at the same time.")

    if exclude is None:
        exclude = []

    if include is None:
        include = [name for name in template.names(True)
                   if name not in exclude]

    for name in include:
        locals[name] = copy_attribute(template.get(name))


def copy_attribute(attribute):
    """Copy an interface attribute.

    This makes sure that the relative ordering of IField is preserved.
    """
    if not IAttribute.providedBy(attribute):
        raise TypeError("%r doesn't provide IAttribute." % attribute)

    new_attribute = copy(attribute)
    # Fields are ordered based on a global counter in the Field class.
    # We increment and use Field.order to reorder the copied fields.
    # If fields are subsequently defined, they they will follow the
    # copied fields.
    if isinstance(new_attribute, Field):
        Field.order += 1
        new_attribute.order = Field.order

    # Reset the interface attribute.
    new_attribute.interface = None

    return new_attribute


def copy_field(field, **overrides):
    """Copy a schema field and set optional field attributes.

    :param field: The IField to copy.
    :param **overrides: dictionary of attributes to override in the copy.
    :returns: the new field.
    """
    if not IField.providedBy(field):
        raise TypeError("%r doesn't provide IField." % field)
    field_copy = copy_attribute(field)

    for name, value in overrides.items():
        setattr(field_copy, name, value)
    return field_copy

