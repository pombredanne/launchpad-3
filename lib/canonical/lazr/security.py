# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for dealing with zope security."""

__metaclass__ = type
__all__ = [
    'protect_schema',
    ]


from zope.interface.interfaces import IMethod
from zope.schema.interfaces import IField
from zope.security.checker import defineChecker, CheckerPublic, Checker


def protect_schema(type_, schema, read_permission=CheckerPublic,
                   write_permission=None):
    """Define security checker based on a schema.

    This will define a checker for the type, based on the names available in
    the schema. All attributes will be protected.
    It also grants set access to attributes and non-readonly fields of
    the schema if the write_permission parameter is used.

    :param type_: The class for which the checker will be defined.
    :param schema: The schema to use to find the names to protect.
    :param read_permission: The permission used to protect access to the
        attributes. Default to public access.
    :param write_permission: If this is not None, set access to the writable
        attributes of the schema will be added to the checker.
    """
    read_permissions = {}
    write_permissions = {}
    for name in schema.names(True):
        read_permissions[name] = read_permission
        if write_permission is not None:
            attribute = schema.get(name)
            # We don't want to set methods or readonly fields.
            if IMethod.providedBy(attribute):
                continue
            if IField.providedBy(attribute) and attribute.readonly:
                continue
            write_permissions[name] = write_permission
    defineChecker(type_, Checker(read_permissions, write_permissions))


