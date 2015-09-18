# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IXRefSet',
    ]

from zope.interface import Interface


class IXRefSet(Interface):

    def createByIDs(xrefs):
        """Create multiple cross-references by object IDs.

        :param xrefs: A collection of dicts of
            {'object_ids': [id1, id2], 'creator': `IPerson`,
             'metadata': arbitrary_json_value}.
        """

    def findByIDs(object_ids):
        """Find all cross-references involving the given object IDs.

        :param object_ids: A collection of object IDs.
        :return: A collection of dicts of
            {'object_ids': [id1, id2], 'creator': `IPerson`,
             'metadata': arbitrary_json_value}.
        """

    def deleteByIDs(object_id_pairs):
        """Delete cross-references by pairs of object IDs.

        :param object_ids: A collection of pairs of object IDs to remove
            references between.
        """

    def findIDs(object_id):
        """Find all object IDs linked to the given object ID.

        :param object_ids: An object ID.
        :return: A list of linked object IDs.
        """
