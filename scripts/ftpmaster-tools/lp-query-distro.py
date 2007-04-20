#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Script to provide easy integration layer with non-native scripts.

   It should provide an easy way to retrieve current information from Launchpad
   System when using plain shell scripts, for example:

   * CURRENT distrorelease name: `./ubuntu-helper.py -d ubuntu current`
   * DEVEVELOPMENT distrorelease name: `./ubuntu-helper.py -d ubuntu development`
   * Distorelease architectures:
       `./ubuntu-helper.py -d ubuntu -s feisty archs`
   * Distorelease official architectures:
       `./ubuntu-helper.py -d ubuntu -s feisty official_archs`
   * Distorelease nominated-arch-indep:
       `./ubuntu-helper.py -d ubuntu -s feisty nominated_arch_indep`
   """


__metaclass__ = type

import _pythonpath

import sys

from zope.component import getUtility

from canonical.config import config

from canonical.launchpad.scripts.ftpmaster import PackageLocation
from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.launchpad.interfaces import IDistributionSet
from canonical.lp.dbschema import DistributionReleaseStatus


class UbuntuHelper(LaunchpadScript):
    allowed_actions = ['current', 'development', 'archs', 'official_archs',
                       'nominated_arch_indep']

    def __init__(self, name, dbuser):
        """XXX."""
        self.usage = '%%prog <%s>' % ','.join(self.allowed_actions)
        LaunchpadScript.__init__(self, name, dbuser)

    def add_my_options(self):
        """XXX."""
        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name', default='ubuntu',
            help='Context distribution name.')
        self.parser.add_option(
            '-s', '--suite', dest='suite_name', default=None,
            help='Context suite name.')

    def main(self):
        """XXX."""
        # Just exit if no action was requested
        if len(self.args) != 1:
            raise LaunchpadScriptFailure('<action> is required')

        [action_name] = self.args
        if action_name not in self.allowed_actions:
            raise LaunchpadScriptFailure(
                'Action "%s" is not allowed' % action_name)

        # Build context location
        self.location = PackageLocation(
            distribution_name = self.options.distribution_name,
            suite_name = self.options.suite_name)

        self.runAction(action_name)

    def presentResult(self, result):
        """Default result presenter.

        Directly prints result in the standard output (print).
        """
        print result

    def runAction(self, action_name, presenter=None):
        """Run a given action.

        It accepts an optional 'presenter' which will be used to
        store/present the action result.
        It may raise LaunchpadScriptFailure is the 'action' is not supported.
        """
        if presenter is None:
            presenter = self.presentResult

        try:
            action_result = getattr(self, 'get_' + action_name)
        except AttributeError:
            raise LaunchpadScriptFailure(
                "'%s' not supported." % action_name)

        presenter(action_result)

    def checkNoSuiteDefined(self):
        """Raises LaunchpadScriptError if a suite location was passed.

        It is re-used in action properties to avoid conflicting contexts,
        i.e, passing an arbitrary 'suite' and asking for the CURRENT suite
        in the context distribution.
        """
        if self.options.suite_name is not None:
            raise LaunchpadScriptFailure(
                "Action does not accept defined suite_name.")

    # XXX cprov 20070420: should be implemented in IDistribution.
    # raising NotFoundError instead.
    def getReleaseByStatus(self, releasestatus):
        """Query context distribution for a distrorelese in a given status.

        I may raise LaunchpadScriptError if no suitable distrorelease in a
        given status was found.
        """
        for release in self.location.distribution.releases:
            if release.releasestatus == releasestatus:
                return release
        raise LaunchpadScriptFailure(
                "Could not find a %s distrorelease in %s"
                % (status.name, self.location.distribution.name))

    @property
    def get_current(self):
        """Return the name of the CURRENT distrorelease.

        It is restricted for the context distribution.
        It may raise LaunchpadScriptFailure if a suite was passed in the
        command-line.
        See self.getReleaseByStatus for further information
        """
        self.checkNoSuiteDefined()
        release = self.getReleaseByStatus(
            DistributionReleaseStatus.CURRENT)
        return release.name

    @property
    def get_development(self):
        """Return the name of the DEVELOPMENT distrorelease.

        It is restricted for the context distribution.
        It may raise LaunchpadScriptFailure if a suite was passed in the
        command-line.
        See self.getReleaseByStatus for further information
        """
        self.checkNoSuiteDefined()
        release = self.getReleaseByStatus(
            DistributionReleaseStatus.DEVELOPMENT)
        return release.name

    @property
    def get_archs(self):
        """Return a space-separated list of architecture tags.

        It is restricted for the context distribution and suite.
        """
        return " ".join([arch.architecturetag for arch in
                         self.location.distrorelease.architectures])
    @property
    def get_official_archs(self):
        """Return a space-separated list of official architecture tags.

        It is restricted for the context distribution and suite.
        """
        return " ".join([arch.architecturetag for arch in
                         self.location.distrorelease.architectures
                         if arch.official])

    @property
    def get_nominated_arch_indep(self):
        """Return the nominated arch indep architecture tag.

        It is restricted for the context distribution and suite.
        """

        """XXX."""
        release = self.location.distrorelease
        return release.nominatedarchindep.architecturetag

    # XXX cprov 20070420: we need to redefine LPScript.run() in order to
    # have quiten exits. We don't want any noise !

if __name__ == '__main__':
    script = UbuntuHelper('ubuntu-helper', dbuser=config.builddmaster.dbuser)
    script.run()

