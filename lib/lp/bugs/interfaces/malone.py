# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces pertaining to the launchpad Malone application."""

__metaclass__ = type

from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    export_as_webservice_collection,
    export_factory_operation,
    export_read_operation,
    operation_for_version,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import Reference
from lazr.restful.interface import copy_field
from zope.interface import Attribute

from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.bugtarget import IBugTarget
from lp.services.webapp.interfaces import ILaunchpadApplication


__all__ = [
    'IMaloneApplication',
    'IPrivateMaloneApplication',
    ]


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""
    export_as_webservice_collection(IBug)

    def searchTasks(search_params):
        """Search IBugTasks with the given search parameters."""

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        bug_id=copy_field(IBug['id']),
        related_bug=Reference(schema=IBug)
    )
    @export_read_operation()
    @operation_for_version('devel')
    def getBugData(user, bug_id, related_bug=None):
        """Search bugtasks matching the specified criteria.

        The only criteria currently supported is to search for a bugtask with
        the specified bug id.

        :return: a list of matching bugs represented as json data
        """

    bug_count = Attribute("The number of bugs recorded in Launchpad")
    bugwatch_count = Attribute("The number of links to external bug trackers")
    bugtask_count = Attribute("The number of bug tasks in Launchpad")
    projects_with_bugs_count = Attribute("The number of products and "
        "distributions which have bugs in Launchpad.")
    shared_bug_count = Attribute("The number of bugs that span multiple "
        "products and distributions")
    bugtracker_count = Attribute("The number of bug trackers in Launchpad")
    top_bugtrackers = Attribute("The BugTrackers with the most watches.")

    @collection_default_content()
    def empty_list():
        """Return an empty set - only exists to keep lazr.restful happy."""

    @call_with(owner=REQUEST_USER)
    @operation_parameters(
        target=Reference(
            schema=IBugTarget, required=True,
            title=u"The project, distribution or source package that has "
                   "this bug."))
    @export_factory_operation(
        IBug, ['title', 'description', 'tags', 'security_related', 'private'])
    def createBug(owner, title, description, target, security_related=None,
                  private=None, tags=None):
        """Create a bug (with an appropriate bugtask) and return it.

        :param target: The Product, Distribution or DistributionSourcePackage
            affected by this bug.

        Things to note when using this factory:

          * the owner will be subscribed to the bug

          * distribution, product and package contacts (whichever ones are
            applicable based on the bug report target) will be subscribed to
            all *public bugs only*

          * for public upstreams bugs where there is no upstream bug contact,
            the product owner will be subscribed instead
        """


class IPrivateMaloneApplication(ILaunchpadApplication):
    """Private application root for malone."""
