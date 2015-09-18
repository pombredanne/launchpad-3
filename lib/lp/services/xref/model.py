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
    __storm_primary__ = "object1_id", "object2_id"

    object1_id = Unicode(allow_none=False)
    object2_id = Unicode(allow_none=False)
    creator_id = Int(name="creator")
    creator = Reference(creator_id, "Person.id")
    metadata = JSON()


@implementer(IXRefSet)
class XRefSet:

    def createByIDs(self, xrefs):
        bulk.create(
            (XRef.object1_id, XRef.object2_id, XRef.creator, XRef.metadata),
            [list(sorted(x['object_ids']))
             + [x.get('creator'), x.get('metadata')]
             for x in xrefs])

    def deleteByIDs(self, object_id_pairs):
        canonical_pairs = [list(sorted(pair)) for pair in object_id_pairs]
        IStore(XRef).find(
            XRef,
            Or(*[
                And(XRef.object1_id == pair[0], XRef.object2_id == pair[1])
                for pair in canonical_pairs])
            ).remove()

    def findByIDs(self, object_ids):
        from lp.registry.model.person import Person

        store = IStore(XRef)
        result = store.using(XRef).find(
            (XRef.object1_id, XRef.object2_id, XRef.creator_id, XRef.metadata),
            Or(
                XRef.object1_id.is_in(object_ids),
                XRef.object2_id.is_in(object_ids)))
        bulk.load(Person, [r[2] for r in result])
        return [
            {"object_ids": [r[0], r[1]], "creator": store.get(Person, r[2]),
             "metadata": r[3]}
            for r in result]

    def findIDs(self, object_id):
        return [
            [id for id in x.get("object_ids") if id != object_id][0]
            for x in self.findByIDs([object_id])]
