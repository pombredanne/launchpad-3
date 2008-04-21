# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Validator for sqlobject attributes.

Restricts the objects that private/private-membership teams
can be connect to.
"""

__metaclass__ = type
__all__ = [
    'public_person_validator',
    'validate_public_person',
    ]

from canonical.lazr.enum import DBItem
from canonical.launchpad.interfaces import IPerson, PersonVisibility
from canonical.launchpad.fields import is_valid_public_person_link


def validate_public_person(obj, attr, value):
    if value is None:
        return None
    assert isinstance(value, (int, long)), (
        "Expected int for Person foreign key reference, got %r" % type(value))

    from canonical.launchpad.database.person import Person
    person = Person.get(value)
    if is_valid_public_person_link(person, obj):
        raise ValueError(
            "Cannot link person (name=%s, visibility=%s) to %s (name=%s)"
            % (person.name, person.visibility.name,
               obj, getattr(obj, 'name', None)))
    return value


# XXX: this needs to be removed when everything is moved over to the
# Storm validator.
public_person_validator = None
