# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz publication override script."""

__metaclass__ = type

__all__ = [
    'ArchiveOverrider',
    'ArchiveOverriderError',
    ]

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.soyuz.enums import PackagePublishingPriority
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )


class ArchiveOverriderError(SoyuzScriptError):
    """ArchiveOverrider specific exception.

    Mostly used to describe errors in the initialization of this object.
    """


class ChangeOverride(SoyuzScript):

    usage = '%prog -s <suite> <package name> [-SBt] [-c component]'
    description = 'OVERRIDE a publication.'

    def add_my_options(self):
        self.add_transaction_options()
        self.add_distro_options()
        self.add_package_location_options()

        self.parser.add_option(
            "-p", "--priority", dest="priority",
            help="move package to PRIORITY")
        self.parser.add_option(
            "-x", "--section", dest="section",
            help="move package to SECTION")

        self.parser.add_option(
            "-S", "--source-and-binary", dest="sourceandchildren",
            default=False, action="store_true",
            help="select source and all binaries from this source")
        self.parser.add_option(
            "-B", "--binary-and-source", dest="binaryandsource",
            default=False, action="store_true",
            help="select source and binary (of the same name)")
        self.parser.add_option(
            "-t", "--source-only", dest="sourceonly",
            default=False, action="store_true",
            help="select source packages only")

    def setupLocation(self):
        SoyuzScript.setupLocation(self)
        self.setupOverrides()

    def setupOverrides(self):
        """Convert override options into the corresponding DB values.

        The results are stored as attributes of this object:

         * 'component': IComponent or None;
         * 'section': ISection or None;
         * 'priority': PackagePublishingPriority or None.
        """
        if self.options.component is not None:
            try:
                self.component = getUtility(IComponentSet)[
                    self.options.component]
            except NotFoundError, err:
                raise SoyuzScriptError(err)
            self.logger.info(
                "Override Component to: '%s'" % self.component.name)
        else:
            self.component = None

        if self.options.section is not None:
            try:
                self.section = getUtility(ISectionSet)[
                    self.options.section]
            except NotFoundError, err:
                raise SoyuzScriptError(err)
            self.logger.info("Override Section to: '%s'" % self.section.name)
        else:
            self.section = None

        if self.options.priority is not None:
            try:
                priority_name = self.options.priority.upper()
                self.priority = PackagePublishingPriority.items[priority_name]
            except KeyError, err:
                raise SoyuzScriptError(err)
            self.logger.info(
                "Override Priority to: '%s'" % self.priority.name)
        else:
            self.priority = None

    def _validatePublishing(self, currently_published):
        """Do not validate found publications, because it's not necessary."""
        pass

    def mainTask(self):
        """Dispatch override operations according togiven options.

        Iterate over multiple targets given as command-line arguments.
        """
        assert self.location, (
            "Location is not available, call PackageCopier.setupLocation() "
            "before dealing with mainTask.")

        for package_name in self.args:
            # Change matching source.
            if (self.options.sourceonly or self.options.binaryandsource or
                self.options.sourceandchildren):
                self.processSourceChange(package_name)

            # Change all binaries for matching source.
            if self.options.sourceandchildren:
                self.processChildrenChange(package_name)
            # Change only binary matching name.
            elif not self.options.sourceonly:
                self.processBinaryChange(package_name)

    def processSourceChange(self, package_name):
        """Perform changes in a given source package name.

        It changes only the current published package release.
        """
        publication = self.findLatestPublishedSource(package_name)

        override = publication.changeOverride(
            new_component=self.component, new_section=self.section)

        if override is None:
            action_banner = "remained the same"
        else:
            action_banner = "source overridden"

        self.logger.info("'%s/%s/%s' %s"
                      % (publication.sourcepackagerelease.title,
                         publication.component.name,
                         publication.section.name, action_banner))

    def processBinaryChange(self, package_name):
        """Override the published binary version in the given context.

        Receive a binary name and a distroarchseries, warns and return if
        no published version could be found.
        """
        binaries = self.findLatestPublishedBinaries(package_name)
        for binary in binaries:
            override = binary.changeOverride(
                new_component=self.component,
                new_priority=self.priority,
                new_section=self.section)

            if override is None:
                action_banner = "remained the same"
            else:
                distroarchseries_title = "%s/%s" % (
                    override.distroarchseries.distroseries.name,
                    override.distroarchseries.architecturetag)
                action_banner = "binary overridden in %s" % (
                    distroarchseries_title)

            self.logger.info(
                "'%s/%s/%s/%s' %s"
                % (binary.binarypackagerelease.title,
                   binary.component.name, binary.section.name,
                   binary.priority.name, action_banner))

    def processChildrenChange(self, package_name):
        """Perform changes on all binary packages generated by this source.

        Affects only the currently published release where the binary is
        directly related to the source version.
        """
        source_pub = self.findLatestPublishedSource(package_name)

        binary_names = set(
            pub.binarypackagerelease.name
            for pub in source_pub.getPublishedBinaries())

        for binary_name in sorted(binary_names):
            self.processBinaryChange(binary_name)

