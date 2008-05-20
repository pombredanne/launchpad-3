# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces pertaining to the launchpad Malone application."""

__metaclass__ = type

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, TextLine
from persistent import IPersistent

from canonical.launchpad import _
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.fields import PublicPersonChoice
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

# XXX kiko 2007-02-08:
# These import shims are actually necessary if we don't go over the
# entire codebase and fix where the import should come from.
from canonical.launchpad.webapp.interfaces import (
    IBasicLaunchpadRequest, IBreadcrumb, ILaunchBag, ILaunchpadRoot,
    IOpenLaunchBag, NotFoundError, UnexpectedFormData,
    UnsafeFormGetSubmissionError)

from canonical.lazr.interface import copy_field
from canonical.lazr.rest.declarations import (
    REQUEST_USER, call_with, collection_default_content,
    export_as_webservice_collection, export_as_webservice_entry,
    export_read_operation, exported, generate_collection_adapter,
    operation_parameters, rename_parameters_as)


__all__ = [
    'IMaloneApplication',
    ]


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""
    export_as_webservice_collection(IBug)

    def searchTasks(search_params):
        """Search IBugTasks with the given search parameters."""

    bug_count = Attribute("The number of bugs recorded in Launchpad")
    bugwatch_count = Attribute("The number of links to external bug trackers")
    bugtask_count = Attribute("The number of bug tasks in Launchpad")
    projects_with_bugs_count = Attribute("The number of products and "
        "distributions which have bugs in Launchpad.")
    shared_bug_count = Attribute("The number of bugs that span multiple "
        "products and distributions")
    bugtracker_count = Attribute("The number of bug trackers in Launchpad")
    top_bugtrackers = Attribute("The BugTrackers with the most watches.")
    latest_bugs = Attribute("The latest 5 bugs filed.")

    @collection_default_content()
    @export_read_operation()
    def default_bug_list():
        """Return a default list of bugs."""
