# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import re

from canonical.buildd.debian import (
    DebianBuildManager,
    DebianBuildState,
    get_build_path,
)
RETCODE_SUCCESS = 0
RETCODE_FAILURE_INSTALL = 200
RETCODE_FAILURE_BUILD_TREE = 201
RETCODE_FAILURE_INSTALL_BUILD_DEPS = 202
RETCODE_FAILURE_BUILD_SOURCE_PACKAGE = 203


def splat_file(path, contents):
    file_obj = open(path, 'w')
    try:
        file_obj.write(contents)
    finally:
        file_obj.close()


def get_chroot_path(build_id, *extra):
    return get_build_path(
        build_id, 'chroot-autobuild', os.environ['HOME'][1:], *extra)


class SourcePackageRecipeBuildState(DebianBuildState):
    BUILD_RECIPE = "BUILD_RECIPE"


class SourcePackageRecipeBuildManager(DebianBuildManager):
    """Build a source package from a bzr-builder recipe."""

    initial_build_state = SourcePackageRecipeBuildState.BUILD_RECIPE

    def __init__(self, slave, buildid):
        DebianBuildManager.__init__(self, slave, buildid)
        self.build_recipe_path = slave._config.get(
            "sourcepackagerecipemanager", "buildrecipepath")

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot."""

        self.recipe_data = extra_args['recipe_data']
        self.suite = extra_args['suite']
        self.component = extra_args['ogrecomponent']
        self.package_name = extra_args['package_name']
        self.author_name = extra_args['author_name']
        self.author_email = extra_args['author_email']
        self.purpose = extra_args['purpose']

        super(SourcePackageRecipeBuildManager, self).initiate(
            files, chroot, extra_args)

    def doRunSbuild(self):
        """Run the sbuild process to build the package."""
        currently_building = get_build_path(
            self._buildid, 'chroot-autobuild/CurrentlyBuilding')
        splat_file(currently_building,
            'Package: %s\n'
            'Suite: %s\n'
            'Component: %s\n'
            'Purpose: %s\n'
            'Build-Debug-Symbols: no\n' %
            (self.package_name, self.suite, self.component, self.purpose))
        os.makedirs(get_chroot_path(self._buildid, 'work'))
        recipe_path = get_chroot_path(self._buildid, 'work/recipe')
        splat_file(recipe_path, self.recipe_data)
        args = [
            "buildrecipe.py", self._buildid, self.author_name,
            self.author_email, self.package_name, self.suite]
        self.runSubProcess(self.build_recipe_path, args)

    def iterate_BUILD_RECIPE(self, retcode):
        """Move from BUILD_RECIPE to the next logical state."""
        if retcode == RETCODE_SUCCESS:
            self.gatherResults()
            print("Returning build status: OK")
        elif retcode == RETCODE_FAILURE_INSTALL_BUILD_DEPS:
            if not self.alreadyfailed:
                tmpLog = self.getTmpLogContents()
                rx = (
                    'The following packages have unmet dependencies:\n'
                    '.*: Depends: ([^ ]*( \([^)]*\))?)')
                mo = re.search(rx, tmpLog, re.M)
                if mo:
                    self._slave.depFail(mo.group(1))
                    print("Returning build status: DEPFAIL")
                    print("Dependencies: " + mo.group(1))
                else:
                    print("Returning build status: Build failed")
                    self._slave.buildFail()
        elif (
            retcode >= RETCODE_FAILURE_INSTALL and
            retcode <= RETCODE_FAILURE_BUILD_SOURCE_PACKAGE):
            # XXX AaronBentley 2009-01-13: We should handle depwait separately
            if not self.alreadyfailed:
                self._slave.buildFail()
                print("Returning build status: Build failed.")
        else:
            if not self.alreadyfailed:
                self._slave.builderFail()
                print("Returning build status: Builder failed.")
        self._state = DebianBuildState.REAP
        self.doReapProcesses()

    def getChangesFilename(self):
        work_path = get_build_path(self._buildid)
        for name in os.listdir(work_path):
            if name.endswith('_source.changes'):
                return os.path.join(work_path, name)

    def gatherResults(self):
        DebianBuildManager.gatherResults(self)
        self._slave.addWaitingFile(get_build_path(self._buildid, 'manifest'))
