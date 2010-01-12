# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.buildd.debian import DebianBuildManager, DebianBuildState


class SourcePackageRecipeBuildState(DebianBuildState):
    BUILD_RECIPE = "BUILD_RECIPE"


class SourcePackageRecipeBuildManager(DebianBuildManager):
    """Build a source package from a bzr-builder recipe."""

    initial_build_state = BinaryPackageBuildState.BUILD_RECIPE

    def __init__(self, slave, buildid):
        DebianBuildManager.__init__(self, slave, buildid)
        self._sbuildpath = slave._config.get("sourcepackagerecipemanager", "buildrecipepath")

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
        # XXX: Replace this method here with something to run your
        # script.
        args = ["sbuild-package", self._buildid ]
        args.extend(self._sbuildargs)
        if self.arch_indep:
            args.extend(["-A"])
        if self.archive_purpose:
            args.extend(["--purpose=" + self.archive_purpose])
        if self.build_debug_symbols:
            args.extend(["--build-debug-symbols"])
        if self.suite:
            args.extend(["--dist=" + self.suite])
        else:
            args.extend(["--dist=autobuild"])
        args.extend(["--comp=" + self.ogre])
        args.extend([self._dscfile])
        self.runSubProcess( self._sbuildpath, args )

    def iterate_BUILD_RECIPE(self, success):
        """Finished the recipe build."""
        # XXX: Replace this method here with something to run your
        # script.
        if success != 0:
        if success != SBuildExitCodes.OK:
            tmpLogHandle = open(os.path.join(self._cachepath, "buildlog"))
            tmpLog = tmpLogHandle.read()
            tmpLogHandle.close()
            if (success == SBuildExitCodes.DEPFAIL or
                success == SBuildExitCodes.PACKAGEFAIL):
                for rx in BuildLogRegexes.GIVENBACK:
                    mo=re.search(rx, tmpLog, re.M)
                    if mo:
                        success = SBuildExitCodes.GIVENBACK

            if success == SBuildExitCodes.DEPFAIL:
                for rx, dep in BuildLogRegexes.DEPFAIL:
                    mo=re.search(rx, tmpLog, re.M)
                    if mo:
                        if not self.alreadyfailed:
                            print("Returning build status: DEPFAIL")
                            print("Dependencies: " + mo.expand(dep))
                            self._slave.depFail(mo.expand(dep))
                            success = SBuildExitCodes.DEPFAIL
                            break
                    else:
                        success = SBuildExitCodes.PACKAGEFAIL

            if success == SBuildExitCodes.GIVENBACK:
                if not self.alreadyfailed:
                    print("Returning build status: GIVENBACK")
                    self._slave.giveBack()
            elif success == SBuildExitCodes.PACKAGEFAIL:
                if not self.alreadyfailed:
                    print("Returning build status: PACKAGEFAIL")
                    self._slave.buildFail()
            elif success >= SBuildExitCodes.BUILDERFAIL:
                # anything else is assumed to be a buildd failure
                if not self.alreadyfailed:
                    print("Returning build status: BUILDERFAIL")
                    self._slave.builderFail()
            self.alreadyfailed = True
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
        else:
            print("Returning build status: OK")
            # XXX: You'll probably need to change gatherResults a little
            # to find your changes file.
            self.gatherResults()
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
