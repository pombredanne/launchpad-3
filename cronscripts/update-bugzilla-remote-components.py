#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
import _pythonpath

import time

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.bzremotecomponentfinder import (
    BugzillaRemoteComponentFinder,
    BugzillaRemoteComponentScraper,
    )

from zope.component import getUtility
from lp.bugs.interfaces.bugtracker import (
    BugTrackerType,
    IBugTrackerSet,
    )
from lp.registry.interfaces.distribution import (
    IDistributionSet,
    IDistribution,
    )

# TODO:
#  - Set up logging
#  - Write tests (look at how other cronscripts test)
#    + When running in test mode, use pre-saved html pages
#    + Make a lplib script to get all bugzillas, and then test them locally

launchpad_components = {
    'libglx': {
        'name': 'libglx',
        'is_visible': True,
        'is_custom': False,
        },
    'DRM/ObsoleteDriver': {
        'name': 'DRM/ObsoleteDriver',
        'is_visible': True,
        'is_custom': False,
        },
    'DRM/other': {
        'name': 'DRM/other',
        'is_visible': False,
        'is_custom': False,
        },
    'DRM/fglrx': {
        'name': 'DRM/fglrx',
        'is_visible': True,
        'is_custom': True,
        },
    'deleted-custom-component': {
        'name': 'deleted-custom-component',
        'is_visible': False,
        'is_custom': True,
        }
    }

class UpdateRemoteComponentsFromBugzilla(LaunchpadCronScript):

    def getBugzillas(self):
        """Look up list of bugzillas known to Launchpad"""
        return bugzillas

    def removedComponents(self, bugzilla_components, launchpad_components):
        deletes = []
        for component in launchpad_components:
            if component.name in bugzilla_components:
                continue

            if component.is_visible and not component.is_custom:
                deletes.append(component)
        return deletes

    def newComponents(self, bugzilla_components, launchpad_components):
        adds = []
        for component in bugzilla_components.itervalues():
            # TODO: launchpad_components is a list...
            if component['name'] not in launchpad_components:
                adds.append(component)
        return adds

    def add_my_options(self):
        # TODO: Make sure options are getting captured into current object
        # TODO: Implement support for these options
        self.parser.add_option(
            "-c", "--clean", dest="opt_clean",
            default="false",
            help="Cleanup all custom added components that have been hidden")
        self.parser.add_option(
            "-b", "--bugtracker", dest="opt_bugtracker",
            help="Update only the bug tracker with this name in launchpad")
        self.parser.add_option(
            "-g", "--component-group", dest="opt_component_group",
            help="Only update components in the specified component group")
        self.parser.add_option(
            "-P", "--purge-first", dest="opt_purge_first",
            default="false",
            help="Purge all data including local customizations before "
                 "importing data from Bugzillas")

    def main(self):
        start_time = time.time()
        #finder = BugzillaRemoteComponentFinder(self.txn, self.logger)

        component_groups_to_add_sql_values = []
        components_to_delete_sql_values = []
        components_to_add_sql_values = []

        lp_bugtrackers = getUtility(IBugTrackerSet)
        for lp_bugtracker in lp_bugtrackers:
            if lp_bugtracker.name == "ubuntu-bugzilla":
                continue 
            if lp_bugtracker.bugtrackertype != BugTrackerType.BUGZILLA:
                continue
            if lp_bugtracker.name == "mozilla.org":
                # TODO: We should permit mozilla, but it errors in the sample data so skip for now
                continue

            bz_bugtracker = BugzillaRemoteComponentScraper(lp_bugtracker.baseurl)
            bz_bugtracker.retrieveProducts()

            for product in bz_bugtracker.products.itervalues():
                #print "%s: %s" %(product['name'], product['components'])

                # Bugzilla's "products" are referred to as "component groups" in Launchpad
                # TODO: ensureRemoteComponentGroup?
                lp_component_group = lp_bugtracker.getRemoteComponentGroup(
                    product['name'])

                if lp_component_group is None:
                    # We need to add both the component group and components
                    lp_component_group = lp_bugtracker.addRemoteComponentGroup(
                        product['name'])

                    for component in bz_components:
                        components_to_add_sql_values.append(
                            "(%s, %d, 'True', 'False')" %(
                                component,
                                lp_component_group.id,
                                ))

                else:
                    lp_components = lp_component_group.components
                    bz_components = product['components']

                    new_comps = self.newComponents(bz_components, lp_components)
                    rm_comps = self.removedComponents(bz_components, lp_components)

                    # Add the new components
                    for component in new_comps:
                        components_to_add_sql_values.append(
                            "(%s, %d, 'True', 'False')" %(
                                component_name,
                                lp_component_group.id,
                            ))

                    # Drop components that were in Bugzilla before but
                    # are missing now
                    for component in rm_comps:
                        components_to_delete_sql_values.append(
                            "(name=%s AND component_group=%d)" %(
                                component,
                                component_group_id,
                                ))

                print product['name']
                print " - add to database:  ", new_comps
                print " - rm from database:  ", rm_comps
                print

        # Store new products
        if len(component_groups_to_add_sql_values)>0:
            store.execute(
                """
                INSERT INTO BugTrackerComponentGroup
                (bug_tracker, name)
                VALUES %s;""" % (', '.join(component_groups_to_add_sql_values)))

        # Remove components that no longer exist
        if len(components_to_delete_sql_values)>0:
            store.execute(
                # TODO: Account for product id
                """
                DELETE FROM BugTrackerComponent
                WHERE %s;""" % ' OR '.join(components_to_delete_sql_values))

        # Store new components
        if len(components_to_add_sql_values)>0:
            store.execute(
                """
                INSERT INTO BugTrackerComponent
                (name, component_group, is_visible, is_custom)
                VALUES %s;""" % ', '.join(components_to_add_sql_values))

        run_time = time.time() - start_time
        print("Time for this run: %.3f seconds." % run_time)


if __name__ == "__main__":

    # TODO: Probably need to establish it as its own dbuser in security.cfg
    updater = UpdateRemoteComponentsFromBugzilla(
        "updateremotecomponent",
        dbuser="checkwatches")
    updater.lock_and_run()
