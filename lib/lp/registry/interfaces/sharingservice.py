# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for sharing service."""


__metaclass__ = type

__all__ = [
    'ISharingService',
    ]

from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_read_operation,
    export_write_operation,
    operation_for_version,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from zope.schema import (
    Choice,
    List,
    )

from lp import _
from lp.app.interfaces.services import IService
from lp.registry.enums import InformationType
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pillar import IPillar


class ISharingService(IService):

    # XXX 2012-02-24 wallyworld bug 939910
    # Need to export for version 'beta' even though we only want to use it in
    # version 'devel'
    export_as_webservice_entry(publish_web_link=False, as_of='beta')

    def getInformationTypes(pillar):
        """Return the allowed information types for the given pillar."""

    def getSharingPermissions():
        """Return the information sharing permissions."""

    @export_read_operation()
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True))
    @operation_for_version('devel')
    def getPillarSharees(pillar):
        """Return people/teams who can see pillar artifacts."""

    @export_write_operation()
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True),
        sharee=Reference(IPerson, title=_('Sharee'), required=True),
        information_types=List(Choice(vocabulary=InformationType)))
    @operation_for_version('devel')
    def updatePillarSharee(pillar, sharee, information_types, user):
        """Ensure sharee has the grants for information types on a pillar."""

    @export_write_operation()
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True),
        sharee=Reference(IPerson, title=_('Sharee'), required=True),
        information_types=List(
            Choice(vocabulary=InformationType), required=False))
    @operation_for_version('devel')
    def deletePillarSharee(pillar, sharee, information_types):
        """Remove a sharee from a pillar.

        :param pillar: the pillar from which to remove access
        :param sharee: the person or team to remove
        :param information_types: if None, remove all access, otherwise just
                                   remove the specified access_policies
        """
