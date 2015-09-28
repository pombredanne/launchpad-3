# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "XRefSet",
    ]

import pytz
from storm.expr import (
    And,
    Or,
    )
from storm.properties import (
    DateTime,
    Int,
    JSON,
    Unicode,
    )
from storm.references import Reference
from zope.interface import implementer

from lp.services.database import bulk
from lp.services.database.constants import UTC_NOW
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.xref.interfaces import IXRefSet


class XRef(StormBase):
    """Cross-reference between two objects.

    For references to local objects (there is currently no other kind),
    another reference in the opposite direction exists.

    The to_id_int and from_id_int columns exist for efficient SQL joins.
    They are set automatically when the ID looks like an integer.
    """

    __storm_table__ = 'XRef'
    __storm_primary__ = "to_type", "to_id", "from_type", "from_id"

    to_type = Unicode(allow_none=False)
    to_id = Unicode(allow_none=False)
    to_id_int = Int()  # For efficient joins.
    from_type = Unicode(allow_none=False)
    from_id = Unicode(allow_none=False)
    from_id_int = Int()  # For efficient joins.
    creator_id = Int(name="creator")
    creator = Reference(creator_id, "Person.id")
    date_created = DateTime(name='date_created', tzinfo=pytz.UTC)
    metadata = JSON()


def _int_or_none(s):
    if s.isdigit():
        return int(s)
    else:
        return None


@implementer(IXRefSet)
class XRefSet:

    def create(self, xrefs):
        # All references are currently to local objects, so add
        # backlinks as well to keep queries in both directions quick.
        # The *_id_int columns are also set if the ID looks like an int.
        rows = []
        for from_, tos in xrefs.items():
            for to, props in tos.items():
                rows.append((
                    from_[0], from_[1], _int_or_none(from_[1]),
                    to[0], to[1], _int_or_none(to[1]),
                    props.get('creator'), props.get('date_created', UTC_NOW),
                    props.get('metadata')))
                rows.append((
                    to[0], to[1], _int_or_none(to[1]),
                    from_[0], from_[1], _int_or_none(from_[1]),
                    props.get('creator'), props.get('date_created', UTC_NOW),
                    props.get('metadata')))
        bulk.create(
            (XRef.from_type, XRef.from_id, XRef.from_id_int,
             XRef.to_type, XRef.to_id, XRef.to_id_int,
             XRef.creator, XRef.date_created, XRef.metadata), rows)

    def delete(self, xrefs):
        # Delete both directions.
        pairs = []
        for from_, tos in xrefs.items():
            for to in tos:
                pairs.extend([(from_, to), (to, from_)])

        IStore(XRef).find(
            XRef,
            Or(*[
                And(XRef.from_type == pair[0][0],
                    XRef.from_id == pair[0][1],
                    XRef.to_type == pair[1][0],
                    XRef.to_id == pair[1][1])
                for pair in pairs])
            ).remove()

    def findFromMany(self, object_ids, types=None):
        from lp.registry.model.person import Person

        store = IStore(XRef)
        rows = list(store.using(XRef).find(
            (XRef.from_type, XRef.from_id, XRef.to_type, XRef.to_id,
             XRef.creator_id, XRef.date_created, XRef.metadata),
            Or(*[
                And(XRef.from_type == id[0], XRef.from_id == id[1])
                for id in object_ids]),
            XRef.to_type.is_in(types) if types is not None else True))
        bulk.load(Person, [row[4] for row in rows])
        result = {}
        for row in rows:
            result.setdefault((row[0], row[1]), {})[(row[2], row[3])] = {
                "creator": store.get(Person, row[4]) if row[4] else None,
                "date_created": row[5],
                "metadata": row[6]}
        return result

    def findFrom(self, object_id, types=None):
        return self.findFromMany([object_id], types=types).get(object_id, {})
