# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'IXRefSet',
    ]

from zope.interface import Interface


class IXRefSet(Interface):
    """Manager of cross-references between objects.

    Each participant in an xref has an "object ID": a tuple of
    (str type, str id).

    All xrefs are currently between local objects, so links always exist
    in both directions, but this can't be assumed to hold in future.
    """

    def create(xrefs):
        """Create cross-references.

        Back-links are automatically created.

        :param xrefs: A dict of
            {from_object_id: {to_object_id:
                {'creator': `IPerson`, 'metadata': value}}}.
            The creator and metadata keys are optional.
        """

    def findFromMultiple(object_ids):
        """Find all cross-references from multiple objects.

        :param object_ids: A collection of object IDs.
        :return: A dict of
            {from_object_id: {to_object_id:
                {'creator': `IPerson`, 'metadata': value}}}.
            The creator and metadata keys are optional.
        """

    def delete(xrefs):
        """Delete cross-references.

        Back-links are automatically deleted.

        :param xrefs: A dict of {from_object_id: [to_object_id]}.
        """

    def findFrom(object_id):
        """Find all cross-references from an object.

        :param object_id: An object ID.
        :return: A dict of
            {to_object_id: {'creator': `IPerson`, 'metadata': value}}.
            The creator and metadata keys are optional.
        """
