# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Validator for sqlobject attributes to restrict the objects
that private/private-membership teams can be connect to.
"""

__metaclass__ = type
__all__ = ['PublicPersonValidator', 'PublicOrPrivatePersonValidator']

from zope.component import getUtility
from sqlobject.include.validators import Validator, InvalidField

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.fields import (
    is_valid_public_person_link, is_valid_public_or_private_person_link)

class PersonValidatorBase(Validator):
    def isValidPersonLink(self, person, state_object):
        """To be overridden in child classes."""
        raise NotImplementedError

    def toPython(self, value, state=None):
        if value is None:
            return value
        elif isinstance(value, int):
            person = getUtility(IPersonSet).get(value)
            if person is None:
                raise InvalidField('No person with id=%d' % value,
                                   value, state)
        elif IPerson.providedBy(value):
            person = value
        else:
            raise InvalidField('Cannot coerce to person object',
                               value,
                               state)
        if not self.isValidPersonLink(person, state.soObject):
            raise InvalidField(
                'Cannot link person (name=%s, visibility=%s) to %s (name=%s)'
                % (person.name, person.visibility.name,
                   state.soObject, getattr(state.soObject, 'name', None)),
                value,
                state)
        return value


class PublicOrPrivatePersonValidator(PersonValidatorBase):
    def isValidPersonLink(self, person, state_object):
        return is_valid_public_or_private_person_link(person, state_object)


class PublicPersonValidator(PersonValidatorBase):
    def isValidPersonLink(self, person, state_object):
        return is_valid_public_person_link(person, state_object)
