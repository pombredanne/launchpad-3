# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Validator for content class attributes.

Restricts the objects that private/private-membership teams
can be connect to.
"""

__metaclass__ = type
__all__ = [
    'validate_person_not_private_membership',
    'validate_public_person',
    ]

from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.fields import (
    is_private_membership, is_valid_public_person)


class PrivatePersonLinkageError(ValueError):
    """An attempt was made to link a private person/team to something."""


@block_implicit_flushes
def validate_public_person(obj, attr, value):
    """Validate that the person identified by value is public."""
    #import pdb; pdb.set_trace(); # DO NOT COMMIT
    if value is None:
        return None
    assert isinstance(value, (int, long)), (
        "Expected int for Person foreign key reference, got %r" % type(value))

    from canonical.launchpad.database.person import Person
    person = Person.get(value)
    if not is_valid_public_person(person):
        raise PrivatePersonLinkageError(
            "Cannot link person (name=%s, visibility=%s) to %s (name=%s)"
            % (person.name, person.visibility.name,
               obj, getattr(obj, 'name', None)))
    return value


@block_implicit_flushes
def validate_person_not_private_membership(obj, attr, value):
    """Validate that the person (value) is not a private membership team."""
    if value is None:
        return None
    assert isinstance(value, (int, long)), (
        "Expected int for Person foreign key reference, got %r" % type(value))

    from canonical.launchpad.database.person import Person
    person = Person.get(value)
    if is_private_membership(person):
        raise PrivatePersonLinkageError(
            "Cannot link person (name=%s, visibility=%s) to %s (name=%s)"
            % (person.name, person.visibility.name,
               obj, getattr(obj, 'name', None)))
    return value
