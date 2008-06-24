# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces pertaining to the launchpad Malone application."""

__metaclass__ = type

from zope.interface import Attribute

from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

from canonical.lazr.rest.declarations import (
    collection_default_content, export_as_webservice_collection, REQUEST_USER)


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

    @collection_default_content(user=REQUEST_USER)
    def default_bug_list(user):
        """Return a default list of bugs.

        :param user: The user who's doing the search.
        """
