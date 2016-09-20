# Copyright 2009-2013 Canonical Ltd.  This software is licensed under
# the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Publisher script class."""

__metaclass__ = type
__all__ = [
    'PublisherScript',
    ]

from optparse import OptionValueError

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import LaunchpadCronScript


class PublisherScript(LaunchpadCronScript):

    def addDistroOptions(self):
        self.parser.add_option(
            "-d", "--distribution", dest="distribution", metavar="DISTRO",
            default=None, help="The distribution to publish.")

        self.parser.add_option(
            "-a", "--all-derived", action="store_true", dest="all_derived",
            default=False, help="Publish all Ubuntu-derived distributions.")

    def findSelectedDistro(self):
        """Find the `Distribution` named by the --distribution option.

        Defaults to Ubuntu if no name was given.
        """
        self.logger.debug("Finding distribution object.")
        name = self.options.distribution
        if name is None:
            # Default to publishing Ubuntu.
            name = "ubuntu"
        distro = getUtility(IDistributionSet).getByName(name)
        if distro is None:
            raise OptionValueError("Distribution '%s' not found." % name)
        return distro

    def findDerivedDistros(self):
        """Find all Ubuntu-derived distributions."""
        self.logger.debug("Finding derived distributions.")
        return getUtility(IDistributionSet).getDerivedDistributions()

    def findDistros(self):
        """Find the selected distribution(s)."""
        if self.options.all_derived:
            return self.findDerivedDistros()
        else:
            return [self.findSelectedDistro()]
