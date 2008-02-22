# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers for working with Zope interface."""

__metaclass__ = type
__all__ = [
        'use_template'
        ]

import sys
from copy import copy

from zope.schema import Field


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
            "you cannot use include and exclude at the same time.")

    if exclude is None:
        exclude = []

    if include is None:
        include = [name for name in template.names(True)
                   if name not in exclude]

    for name in include:
        field = copy(template.get(name))
        # Field are ordered based on a counter in the Field class. We want
        # the new fields to be re-ordered, so we need to use that property.
        if isinstance(field, Field):
            Field.order += 1
            field.order = Field.order
        locals[name] = field

