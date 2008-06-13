# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Validator for sqlobject attributes.

Restricts the objects that private/private-membership teams
can be connect to.
"""

__metaclass__ = type
__all__ = [
    'validate_public_person',
    ]

from canonical.database.sqlbase import block_implicit_flushes
from canonical.lazr.enum import DBItem
from canonical.launchpad.interfaces import IPerson, PersonVisibility
from canonical.launchpad.fields import is_valid_public_person_link


class PrivatePersonLinkageError(ValueError):
    """An attempt was made to link a private person/team to something."""


@block_implicit_flushes
def validate_public_person(obj, attr, value):
    """Validate that the the person identified by value is public."""
    if value is None:
        return None
    assert isinstance(value, (int, long)), (
        "Expected int for Person foreign key reference, got %r" % type(value))

    from canonical.launchpad.database.person import Person
    person = Person.get(value)
    if not is_valid_public_person_link(person, obj):
        raise PrivatePersonLinkageError(
            "Cannot link person (name=%s, visibility=%s) to %s (name=%s)"
            % (person.name, person.visibility.name,
               obj, getattr(obj, 'name', None)))
    return value
