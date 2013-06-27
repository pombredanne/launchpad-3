# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enterprise ID utilities."""

__metaclass__ = type
__all__ = [
    'object_to_enterpriseid',
    'enterpriseids_to_objects',
    ]

from collections import defaultdict
import os

from lp.services.config import config
from lp.services.database.bulk import load


def object_to_enterpriseid(obj):
    """Given an object, convert it to SOA Enterprise ID."""
    otype = obj.__class__.__name__
    instance = 'lp'
    if config.devmode:
        instance += '-development'
    elif os.environ['LPCONFIG'] in ('dogfood', 'qastaing', 'staging'):
        instance += '-%s' % os.environ['LPCONFIG']
    return '%s:%s:%d' % (instance, otype, obj.id)


def _known_types():
    # Circular imports.
    from lp.registry.model.person import Person
    from lp.soyuz.model.queue import PackageUpload
    return {
        'PackageUpload': PackageUpload,
        'Person': Person,
    }


def enterpriseids_to_objects(eids):
    """Given a list of SOA Enterprise IDs, return a dict that maps the ID to
    its concrete object."""
    map_id_to_obj = {}
    obj_id_to_eid = defaultdict(dict)
    type_ids = _known_types()
    for kind in type_ids:
        type_ids[kind] = []
    for eid in eids:
        if not eid.startswith('lp'):
            raise TypeError
        map_id_to_obj[eid] = None
        scheme = eid.split(':')
        type_ids[scheme[1]].append(int(scheme[2]))
        obj_id_to_eid[scheme[1]][int(scheme[2])] = eid
    types = _known_types()
    for kind in types:
        objs = load(types[kind], type_ids[kind])
        for obj in objs:
            map_id_to_obj[obj_id_to_eid[kind][obj.id]] = obj
    return map_id_to_obj
