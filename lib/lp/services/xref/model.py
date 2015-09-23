# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "XRefSet",
    ]

from storm.expr import (
    And,
    Or,
    )
from storm.properties import (
    Int,
    JSON,
    Unicode,
    )
from storm.references import Reference
from zope.interface import implementer

from lp.services.database import bulk
from lp.services.database.interfaces import IStore
from lp.services.database.stormbase import StormBase
from lp.services.xref.interfaces import IXRefSet


class XRef(StormBase):

    __storm_table__ = 'XRef'
    __storm_primary__ = "to_type", "to_id", "from_type", "from_id"

    to_type = Unicode(allow_none=False)
    to_id = Unicode(allow_none=False)
    to_id_int = Int()
    from_type = Unicode(allow_none=False)
    from_id = Unicode(allow_none=False)
    from_id_int = Int()
    creator_id = Int(name="creator")
    creator = Reference(creator_id, "Person.id")
    metadata = JSON()


@implementer(IXRefSet)
class XRefSet:

    def create(self, xrefs):
        # All references are currently to local objects, so add
        # backlinks as well to keep queries in both directions quick.
        rows = []
        for from_, tos in xrefs.items():
            for to, props in tos.items():
                rows.append((
                    from_[0], from_[1], to[0], to[1], props.get('creator'),
                    props.get('metadata')))
                rows.append((
                    to[0], to[1], from_[0], from_[1], props.get('creator'),
                    props.get('metadata')))
        bulk.create(
            (XRef.from_type, XRef.from_id, XRef.to_type, XRef.to_id,
             XRef.creator, XRef.metadata), rows)

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

    def findFromMultiple(self, object_ids):
        from lp.registry.model.person import Person

        store = IStore(XRef)
        rows = list(store.using(XRef).find(
            (XRef.from_type, XRef.from_id, XRef.to_type, XRef.to_id,
             XRef.creator_id, XRef.metadata),
            Or(*[
                And(XRef.from_type == id[0], XRef.from_id == id[1])
                for id in object_ids])))
        bulk.load(Person, [row[4] for row in rows])
        result = {}
        for row in rows:
            result.setdefault((row[0], row[1]), {})[(row[2], row[3])] = {
                "creator": store.get(Person, row[4]) if row[4] else None,
                "metadata": row[5]}
        return result

    def findFrom(self, object_id):
        return self.findFromMultiple([object_id]).get(object_id, {})
