# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enterprise ID utilities."""

__metaclass__ = type
__all__ = [
    'object_to_enterpriseid',
    'enterpriseid_to_object',
    ]

import os

from lp.registry.model.person import Person
from lp.services.config import config


known_types = {
    'Person': Person,
    }


def object_to_enterpriseid(obj):
    """Given an object, convert it to SOA Enterprise ID."""
    otype = obj.__class__.__name__
    instance = 'lp'
    if config.devmode:
        instance += '-development'
    elif os.environ['LPCONFIG'] in ('dogfood', 'qastaing', 'staging'):
        instance += '-%s' % os.environ['LPCONFIG']
    return '%s:%s:%d' % (instance, otype, obj.id)


def enterpriseid_to_object(eid):
    """Given an SOA Enterprise ID, return the object that it references."""
    scheme = eid.split(':')
    if not scheme[0].startswith('lp'):
        raise TypeError
    klass = known_types[scheme[1]]
    return klass.get(scheme[2])
