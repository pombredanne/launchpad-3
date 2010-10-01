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
    )

# TODO:
#  - Set up logging
#  - Write tests
#    + Examine ./lib/lp/registry/tests/sfremoteproductfinder.py
#    + Examine ./lib/lp/bugs/doc/sourceforge-remote-products.txt
#    + When running in test mode, use pre-saved html pages
#    + Make a lplib script to get all bugzillas, and then test them locally
#
#    * Retrieval of url fails with 500 error when getting page
#    * 

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
        finder = BugzillaRemoteComponentFinder(self.txn, self.logger)
        finder.getRemoteProductsAndComponents()

        run_time = time.time() - start_time
        print("Time for this run: %.3f seconds." % run_time)


if __name__ == "__main__":

    # TODO: Probably need to establish it as its own dbuser in security.cfg
    updater = UpdateRemoteComponentsFromBugzilla(
        "updateremotecomponent",
        dbuser="checkwatches")
    updater.lock_and_run()
