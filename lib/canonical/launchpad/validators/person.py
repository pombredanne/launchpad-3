# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Validator for sqlobject attributes.

Restricts the objects that private/private-membership teams
can be connect to.
"""

__metaclass__ = type
__all__ = ['public_person_validator']

#from sqlobject.include.validators import Validator, InvalidField

from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.fields import is_valid_public_person_link

# class PersonValidatorBase(Validator):
#     def isValidPersonLink(self, person, state_object):
#         """To be overridden in child classes."""
#         raise NotImplementedError

#     def fromPython(self, value, state=None):
#         if value is None:
#             return value
#         elif isinstance(value, (int, long)):
#             # getUtility() can't be used since an interaction may not have
#             # been started.
#             from canonical.launchpad.database.person import PersonSet
#             person = PersonSet().get(value)
#             if person is None:
#                 raise InvalidField('No person with id=%d' % value,
#                                    value, state)
#         elif IPerson.providedBy(value):
#             person = value
#         else:
#             raise InvalidField('Cannot coerce to person object',
#                                value,
#                                state)
#         if not self.isValidPersonLink(person, state.soObject):
#             raise InvalidField(
#                 'Cannot link person (name=%s, visibility=%s) to %s (name=%s)'
#                 % (person.name, person.visibility.name,
#                    state.soObject, getattr(state.soObject, 'name', None)),
#                 value,
#                 state)
#         return value


# class PublicPersonValidatorClass(PersonValidatorBase):
#     def isValidPersonLink(self, person, state_object):
#         return is_valid_public_person_link(person, state_object)


public_person_validator = None # PublicPersonValidatorClass()
