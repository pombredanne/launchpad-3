#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
import _pythonpath

import os
import sys
import re
import pycurl
import time

from StringIO import StringIO

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.bzremotecomponentfinder import (
    BugzillaRemoteComponentFinder,
    LaunchpadBugTracker)


class UpdateRemoteComponentsFromBugzilla(LaunchpadCronScript):

    def getBugzillas(self):
        # TODO: Lookup list of bugzillas from launchpad
        bugzillas = [
            {'name': 'freedesktop-bugs',
             'url': 'http://bugs.freedesktop.org'},
            {'name': 'gnome-bugs',
             'url': 'http://bugs.gnome.org'},
            ]
        return bugzillas

    def removedComponents(self, bugzilla_components, launchpad_components):
        deletes = []
        for component in launchpad_components.itervalues():
            if component['name'] in bugzilla_components:
                continue

            if component['is_visible'] and not component['is_custom']:
                deletes.append(component)
        return deletes

    def newComponents(self, bugzilla_components, launchpad_components):
        adds = []
        for component in bugzilla_components.itervalues():
            if component['name'] not in launchpad_components:
                adds.append(component)
        return adds

    def add_my_options(self):
        # TODO: Make sure options are getting captured into current object
        # TODO: Implement support for these options
        self.parser.add_option(
            "-c", "--clean", dest="opt_clean",
            default="false",
            help="Drop all custom added components that are now deleted")
        self.parser.add_option(
            "-b", "--bugtracker", dest="opt_bugtracker",
            help="Update only the bug tracker with this name in launchpad")
        self.parser.add_option(
            "-g", "--component-group", dest="opt_component_group",
            help="Only update components in this specific component group")
        self.parser.add_option(
            "-P", "--purge-first", dest="opt_purge_first",
            default="false",
            help="Purge all data including local customizations before "
                 "importing data from Bugzillas")


# TODO:
# Cargo cult from update-sourceforge-remote-products.py
# Set up as a cron job (how?)
# Do updates to the database

    def main(self):
        # TODO: If a bz url was specified, run against only it

        start_time = time.time()

        # TODO: Replace this with the actual database object
        distro = 'ubuntu'

        for bugzilla in self.getBugzillas():
            lp_bugtracker = LaunchpadBugTracker(bugzilla['name'])
            lp_bugtracker.retrieveProducts()

            bz_bugtracker = BugzillaRemoteComponentFinder(bugzilla['url'])
            bz_bugtracker.retrieveProducts()

            for product in bz_bugtracker.products.itervalues():
                #print "%s: %s" %(product['name'], product['components'])

                bz_components = product['components']
                lp_components = lp_bugtracker.components(product['name'])

                new_comps = self.newComponents(bz_components, lp_components)
                rm_comps = self.removedComponents(bz_components, lp_components)

                # TODO: Apply changes to launchpad database
                print product['name']
                print " - add to database:  ", new_comps
                print " - rm from database:  ", rm_comps
                print

        run_time = time.time() - start_time
        print("Time for this run: %.3f seconds." % run_time)


if __name__ == "__main__":

    # TODO: Probably need to establish it as its own dbuser in security.cfg
    updater = UpdateRemoteComponentsFromBugzilla(
        "updateremotecomponent",
        dbuser="checkwatches")
    updater.lock_and_run()
