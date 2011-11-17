# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=E1002

"""The manager class for building packages from recipes."""

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
    """Write a string to the specified path.

    :param path: The path to store the string in.
    :param contents: The string to write to the file.
    """
    file_obj = open(path, 'w')
    try:
        file_obj.write(contents)
    finally:
        file_obj.close()


def get_chroot_path(build_id, *extra):
    """Return a path within the chroot.

    :param build_id: The build_id of the build.
    :param extra: Additional path elements.
    """
    return get_build_path(
        build_id, 'chroot-autobuild', os.environ['HOME'][1:], *extra)


class SourcePackageRecipeBuildState(DebianBuildState):
    """The set of states that a recipe build can be in."""
    BUILD_RECIPE = "BUILD_RECIPE"


class SourcePackageRecipeBuildManager(DebianBuildManager):
    """Build a source package from a bzr-builder recipe."""

    initial_build_state = SourcePackageRecipeBuildState.BUILD_RECIPE

    def __init__(self, slave, buildid):
        """Constructor.

        :param slave: A build slave device.
        :param buildid: The id of the build (a str).
        """
        DebianBuildManager.__init__(self, slave, buildid)
        self.build_recipe_path = slave._config.get(
            "sourcepackagerecipemanager", "buildrecipepath")

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot.

        :param files: The files sent by the manager with the request.
        :param chroot: The sha1sum of the chroot to use.
        :param extra_args: A dict of extra arguments.
        """
        self.recipe_text = extra_args['recipe_text']
        self.suite = extra_args['suite']
        self.component = extra_args['ogrecomponent']
        self.author_name = extra_args['author_name']
        self.author_email = extra_args['author_email']
        self.archive_purpose = extra_args['archive_purpose']
        self.distroseries_name = extra_args['distroseries_name']

        super(SourcePackageRecipeBuildManager, self).initiate(
            files, chroot, extra_args)

    def doRunBuild(self):
        """Run the build process to build the source package."""
        os.makedirs(get_chroot_path(self._buildid, 'work'))
        recipe_path = get_chroot_path(self._buildid, 'work/recipe')
        splat_file(recipe_path, self.recipe_text)
        args = [
            "buildrecipe", self._buildid, self.author_name.encode('utf-8'),
            self.author_email, self.suite, self.distroseries_name,
            self.component, self.archive_purpose]
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
            self.alreadyfailed = True
        elif (
            retcode >= RETCODE_FAILURE_INSTALL and
            retcode <= RETCODE_FAILURE_BUILD_SOURCE_PACKAGE):
            # XXX AaronBentley 2009-01-13: We should handle depwait separately
            if not self.alreadyfailed:
                self._slave.buildFail()
                print("Returning build status: Build failed.")
            self.alreadyfailed = True
        else:
            if not self.alreadyfailed:
                self._slave.builderFail()
                print("Returning build status: Builder failed.")
            self.alreadyfailed = True
        self._state = DebianBuildState.REAP
        self.doReapProcesses()

    def getChangesFilename(self):
        """Return the path to the changes file."""
        work_path = get_build_path(self._buildid)
        for name in os.listdir(work_path):
            if name.endswith('_source.changes'):
                return os.path.join(work_path, name)

    def gatherResults(self):
        """Gather the results of the build and add them to the file cache.

        The primary file we care about is the .changes file.
        The manifest is also a useful record.
        """
        DebianBuildManager.gatherResults(self)
        self._slave.addWaitingFile(get_build_path(self._buildid, 'manifest'))
