# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.buildd.debian import DebianBuildManager, DebianBuildState
RETCODE_SUCCESS = 0
RETCODE_FAILURE_INSTALL = 200
RETCODE_FAILURE_BUILD_TREE = 201
RETCODE_FAILURE_INSTALL_BUILD_DEPS = 202
RETCODE_FAILURE_BUILD_SOURCE_PACKAGE = 203


class SourcePackageRecipeBuildState(DebianBuildState):
    BUILD_RECIPE = "BUILD_RECIPE"


class SourcePackageRecipeBuildManager(DebianBuildManager):
    """Build a source package from a bzr-builder recipe."""

    initial_build_state = SourcePackageRecipeState.BUILD_RECIPE

    def __init__(self, slave, buildid):
        DebianBuildManager.__init__(self, slave, buildid)
        self.build_recipe_path = slave._config.get(
            "sourcepackagerecipemanager", "buildrecipepath")

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot."""

        self.recipe_data = extra_args['recipe_data']
        self.suite = extra_args['suite']
        self.package_name = extra_args['package_name']
        self.author_name = extra_args['author_name']
        self.author_email = extra_args['author_email']

        super(SourcePackageRecipeBuildManager, self).initiate(
            files, chroot, extra_args)

    def doRunSbuild(self):
        """Run the sbuild process to build the package."""
        args = ["buildrecipe.py", self._buildid, self.recipe_data,
        self.author_name, self.author_email, self.package_name, self.suite]
        self.runSubProcess(self.build_recipe_path, args)

    def iterate_BUILD_RECIPE(self, retcode):
        """Move from BUILD_RECIPE to the next logical state."""
        if retcode == RETCODE_SUCCESS:
            self.gatherResults()
            print("Returning build status: OK")
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
        for name in os.listdir(get_buildpath(self._buildid, 'work')):
            if name.endswith('_source.changes'):
                return get_buildpath(self._buildid, 'work', name)

    def gatherResults(self):
        DebianBuildManager.gatherResults(self)
        self._slave.addWaitingFile(
            get_buildpath(self._buildid, 'work/manifest'))
