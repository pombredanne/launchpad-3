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

    def createByIDs(self, xrefs):
        # All references are currently to local objects, so add
        # backlinks as well to keep queries in both directions quick.
        rows = []
        for ids, props in xrefs.items():
            ids = list(sorted(ids))
            rows.append((
                '', ids[0], '', ids[1], props.get('creator'),
                props.get('metadata')))
            rows.append((
                '', ids[1], '', ids[0], props.get('creator'),
                props.get('metadata')))
        bulk.create(
            (XRef.from_type, XRef.from_id, XRef.to_type, XRef.to_id,
             XRef.creator, XRef.metadata), rows)

    def deleteByIDs(self, object_id_pairs):
        # Delete both directions.
        pairs = [tuple(pair) for pair in object_id_pairs]
        pairs += [(pair[1], pair[0]) for pair in pairs]

        IStore(XRef).find(
            XRef,
            Or(*[
                And(XRef.from_id == pair[0], XRef.to_id == pair[1])
                for pair in pairs])
            ).remove()

    def findByIDs(self, object_ids):
        from lp.registry.model.person import Person

        store = IStore(XRef)
        result = list(store.using(XRef).find(
            (XRef.from_id, XRef.to_id, XRef.creator_id, XRef.metadata),
            XRef.from_id.is_in(object_ids)))
        bulk.load(Person, [r[2] for r in result])
        return {
            (r[0], r[1]): {
                "creator": store.get(Person, r[2]), "metadata": r[3]}
            for r in result}

    def findIDs(self, object_id):
        return [
            [id for id in ids if id != object_id][0]
            for ids in self.findByIDs([object_id]).keys()]
