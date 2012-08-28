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
    Dict,
    List,
    )

from lp import _
from lp.app.interfaces.services import IService
from lp.bugs.interfaces.bug import IBug
from lp.code.interfaces.branch import IBranch
from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pillar import IPillar


class ISharingService(IService):

    # XXX 2012-02-24 wallyworld bug 939910
    # Need to export for version 'beta' even though we only want to use it in
    # version 'devel'
    export_as_webservice_entry(publish_web_link=False, as_of='beta')

    def checkPillarAccess(pillar, information_type, person):
        """Check the person's access to the given pillar and information type.

        :return: True if the user has access to all the pillar's information
            of that type, False otherwise
        """

    def getAccessPolicyGrantCounts(pillar):
        """Return the number of grantees who have policy grants of each type.

        Returns a resultset of (InformationType, count) tuples, where count is
        the number of grantees who have an access policy grant for the
        information type.
        """

    def getSharedArtifacts(pillar, person, user):
        """Return the artifacts shared between the pillar and person.

        The result includes bugtasks rather than bugs since this is what the
        pillar filtering is applied to and is what the calling code uses.
        The shared bug can be obtained simply by reading the bugtask.bug
        attribute.

        :param user: the user making the request. Only artifacts visible to the
             user will be included in the result.
        :return: a (bugtasks, branches) tuple
        """

    def getVisibleArtifacts(person, branches=None, bugs=None):
        """Return the artifacts shared with person.

        Given lists of artifacts, return those a person has access to either
        via a policy grant or artifact grant.

        :param person: the person whose access is being checked.
        :param branches: the branches to check for which a person has access.
        :param bugs: the bugs to check for which a person has access.
        :return: a collection of artifacts the person can see.
        """

    def getInvisibleArtifacts(person, branches=None, bugs=None):
        """Return the artifacts which are not shared with person.

        Given lists of artifacts, return those a person does not have access to
        either via a policy grant or artifact grant.
        * Do not export this method to the API since it could be used to gain
          access to private information. Internal use only. *

        :param person: the person whose access is being checked.
        :param branches: the branches to check for which a person has access.
        :param bugs: the bugs to check for which a person has access.
        :return: a collection of artifacts the person can not see.
        """

    def getPeopleWithoutAccess(concrete_artifact, people):
        """Return the people who cannot access an artifact.

        Given a list of people, return those who do not have access to the
        specified bug or branch.

        :param concrete_artifact: the bug or branch whose access is being
            checked.
        :param people: the people whose access is being checked.
        :return: a collection of people without access to the artifact.
        """

    def getInformationTypes(pillar):
        """Return the allowed information types for the given pillar."""

    def getBugSharingPolicies(pillar):
        """Return the allowed bug sharing policies for the given pillar."""

    def getBranchSharingPolicies(pillar):
        """Return the allowed branch sharing policies for the given pillar."""

    def getSharingPermissions():
        """Return the information sharing permissions."""

    def getPillarGrantees(pillar):
        """Return people/teams who can see pillar artifacts."""

    @export_read_operation()
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True))
    @operation_for_version('devel')
    def getPillarGranteeData(pillar):
        """Return people/teams who can see pillar artifacts.

        The result records are json data which includes:
            - person name
            - permissions they have for each information type.
        """

    def jsonGranteeData(grant_permissions):
        """Return people/teams who can see pillar artifacts.

        :param grant_permissions: a list of (grantee, accesspolicy, permission)
            tuples.

        The result records are json data which includes:
            - person name
            - permissions they have for each information type.
        """

    @export_write_operation()
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True),
        grantee=Reference(IPerson, title=_('Grantee'), required=True),
        permissions=Dict(
            key_type=Choice(vocabulary=InformationType),
            value_type=Choice(vocabulary=SharingPermission)))
    @operation_for_version('devel')
    def sharePillarInformation(pillar, grantee, user, permissions):
        """Ensure grantee has the grants for information types on a pillar.

        :param pillar: the pillar for which to grant access
        :param grantee: the person or team to grant
        :param user: the user making the request
        :param permissions: a dict of {InformationType: SharingPermission}
            if SharingPermission is ALL, then create an access policy grant
            if SharingPermission is SOME, then remove any access policy grants
            if SharingPermission is NONE, then remove all grants for the access
            policy
        """

    @export_write_operation()
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True),
        grantee=Reference(IPerson, title=_('Grantee'), required=True),
        information_types=List(
            Choice(vocabulary=InformationType), required=False))
    @operation_for_version('devel')
    def deletePillarGrantee(pillar, grantee, user, information_types):
        """Remove a grantee from a pillar.

        :param pillar: the pillar from which to remove access
        :param grantee: the person or team to remove
        :param user: the user making the request
        :param information_types: if None, remove all access, otherwise just
                                   remove the specified access_policies
        """

    @export_write_operation()
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        pillar=Reference(IPillar, title=_('Pillar'), required=True),
        grantee=Reference(IPerson, title=_('Grantee'), required=True),
        bugs=List(
            Reference(schema=IBug), title=_('Bugs'), required=False),
        branches=List(
            Reference(schema=IBranch), title=_('Branches'), required=False))
    @operation_for_version('devel')
    def revokeAccessGrants(pillar, grantee, user, branches=None, bugs=None):
        """Remove a grantee's access to the specified artifacts.

        :param pillar: the pillar from which to remove access
        :param grantee: the person or team for whom to revoke access
        :param user: the user making the request
        :param bugs: the bugs for which to revoke access
        :param branches: the branches for which to revoke access
        """

    @export_write_operation()
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        grantees=List(
            Reference(IPerson, title=_('Grantee'), required=True)),
        bugs=List(
            Reference(schema=IBug), title=_('Bugs'), required=False),
        branches=List(
            Reference(schema=IBranch), title=_('Branches'), required=False))
    @operation_for_version('devel')
    def ensureAccessGrants(grantees, user, branches=None, bugs=None):
        """Ensure a grantee has an access grant to the specified artifacts.

        :param grantees: the people or teams for whom to grant access
        :param user: the user making the request
        :param bugs: the bugs for which to grant access
        :param branches: the branches for which to grant access
        """
