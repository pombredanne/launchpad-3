# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""IHasBuildRecords interface.

Implemented by any object that can have `IBuild` records related to it.
"""

__metaclass__ = type

__all__ = [
    'IHasBuildRecords',
    ]

from zope.interface import Interface
from zope.schema import Choice, TextLine
from lazr.enum import DBEnumeratedType

from canonical.launchpad import _
from lazr.restful.declarations import (
    REQUEST_USER, call_with, export_read_operation, operation_parameters,
    operation_returns_collection_of, rename_parameters_as)


class IHasBuildRecords(Interface):
    """An Object that has build records"""

    @rename_parameters_as(name="source_name")
    @operation_parameters(
        name=TextLine(title=_("Source package name"), required=False),
        build_state=Choice(
            title=_('Build status'), required=False,
            description=_('The status of this build record'),
            # Really a BuildStatus see _schema_circular_imports.
            vocabulary=DBEnumeratedType),
        pocket=Choice(
            title=_("Pocket"), required=False, readonly=True,
            description=_("The pocket into which this entry is published"),
            # Really a PackagePublishingPocket see _schema_circular_imports.
            vocabulary=DBEnumeratedType))
    @call_with(user=REQUEST_USER)
    # Really a IBuild see _schema_circular_imports.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getBuildRecords(build_state=None, name=None, pocket=None,
                        user=None):
        """Return build records in the context it is implemented.

        It excludes build records generated by Gina (imported from a external
        repository), where `IBuild.datebuilt` is null and `IBuild.buildstate`
        is `BuildStatus.FULLYBUILT`.

        The result is simply not filtered if the optional filters are omitted
        by call sites.

        :param build_state: optional `BuildStatus` value for filtering build
            records;
        :param name: optional string for filtering build source package name.
            Sub-string matching is allowed via SQL LIKE.
        :param pocket: optional `PackagePublishingPocket` value for filtering
            build records;
        :param user: optional `IPerson` corresponding to the user performing
            the request. It will filter out build records for which the user
            have no 'view' permission.

        :return: a result set containing `IBuild` records ordered by descending
            `IBuild.datebuilt` except when builds are filtered by
            `BuildStatus.NEEDSBUILD`, in this case records are ordered by
            descending `BuildQueue.lastscore` (dispatching order).
        """
