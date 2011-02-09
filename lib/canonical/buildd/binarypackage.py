# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


import re

from canonical.buildd.debian import DebianBuildManager, DebianBuildState


class SBuildExitCodes:
    """SBUILD process result codes."""
    OK = 0
    DEPFAIL = 1
    GIVENBACK = 2
    PACKAGEFAIL = 3
    BUILDERFAIL = 4


class BuildLogRegexes:
    """Build log regexes for performing actions based on regexes, and extracting dependencies for auto dep-waits"""
    GIVENBACK = [
        ("^E: There are problems and -y was used without --force-yes"),
        ]
    DEPFAIL = [
        ("(?P<pk>[\-+.\w]+)\(inst [^ ]+ ! >> wanted (?P<v>[\-.+\w:~]+)\)","\g<pk> (>> \g<v>)"),
        ("(?P<pk>[\-+.\w]+)\(inst [^ ]+ ! >?= wanted (?P<v>[\-.+\w:~]+)\)","\g<pk> (>= \g<v>)"),
        ("(?s)^E: Couldn't find package (?P<pk>[\-+.\w]+)(?!.*^E: Couldn't find package)","\g<pk>"),
        ("(?s)^E: Package '?(?P<pk>[\-+.\w]+)'? has no installation candidate(?!.*^E: Package)","\g<pk>"),
        ("(?s)^E: Unable to locate package (?P<pk>[\-+.\w]+)(?!.*^E: Unable to locate package)", "\g<pk>"),
        ]


class BinaryPackageBuildState(DebianBuildState):
    SBUILD = "SBUILD"


class BinaryPackageBuildManager(DebianBuildManager):
    """Handle buildd building for a debian style binary package build"""

    initial_build_state = BinaryPackageBuildState.SBUILD

    def __init__(self, slave, buildid):
        DebianBuildManager.__init__(self, slave, buildid)
        self._sbuildpath = slave._config.get("binarypackagemanager", "sbuildpath")
        self._sbuildargs = slave._config.get("binarypackagemanager",
                                             "sbuildargs").split(" ")

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot."""

        self._dscfile = None
        for f in files:
            if f.endswith(".dsc"):
                self._dscfile = f
        if self._dscfile is None:
            raise ValueError, files

        self.archive_purpose = extra_args.get('archive_purpose')
        self.suite = extra_args.get('suite')
        self.component = extra_args['ogrecomponent']
        self.arch_indep = extra_args.get('arch_indep', False)
        self.build_debug_symbols = extra_args.get('build_debug_symbols', False)

        super(BinaryPackageBuildManager, self).initiate(
            files, chroot, extra_args)

    def doRunBuild(self):
        """Run the sbuild process to build the package."""
        args = ["sbuild-package", self._buildid, self.arch_tag]
        if self.suite:
            args.extend([self.suite])
            args.extend(self._sbuildargs)
            args.extend(["--dist=" + self.suite])
        else:
            args.extend(['autobuild'])
            args.extend(self._sbuildargs)
            args.extend(["--dist=autobuild"])
        if self.arch_indep:
            args.extend(["-A"])
        if self.archive_purpose:
            args.extend(["--purpose=" + self.archive_purpose])
        if self.build_debug_symbols:
            args.extend(["--build-debug-symbols"])
        args.extend(["--architecture=" + self.arch_tag])
        args.extend(["--comp=" + self.component])
        args.extend([self._dscfile])
        self.runSubProcess( self._sbuildpath, args )

    def iterate_SBUILD(self, success):
        """Finished the sbuild run."""
        tmpLog = self.getTmpLogContents()
        if success != SBuildExitCodes.OK:
            if (success == SBuildExitCodes.DEPFAIL or
                success == SBuildExitCodes.PACKAGEFAIL):
                for rx in BuildLogRegexes.GIVENBACK:
                    mo = re.search(rx, tmpLog, re.M)
                    if mo:
                        success = SBuildExitCodes.GIVENBACK

            if success == SBuildExitCodes.DEPFAIL:
                for rx, dep in BuildLogRegexes.DEPFAIL:
                    mo = re.search(rx, tmpLog, re.M)
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
            self.gatherResults()
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
