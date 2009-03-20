# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationBranchApprover',
    ]

import os.path

from zope.component import getUtility

from canonical.launchpad.interfaces.potemplate import IPOTemplateSet
from canonical.launchpad.interfaces.translationimportqueue import (
    RosettaImportStatus)
from canonical.launchpad.translationformat.translation_import import (
    TranslationImporter)


class TranslationBranchApprover(object):
    """Automatic approval of translation import files."""

    GENERIC_TEMPLATE_NAMES = [
        'en-US.xpi',
        'messages.pot',
        'untitled.pot',
        'template.pot',
        ]
    GENERIC_TEMPLATE_DIRS = [
        'po',
        ]

    def __init__(self, files, productseries=None,
                 distroseries=None, sourcepackagename=None):
        """Create the approver and build the approval list by comparing
        the given files as found in the source tree to the database entries.

        Either productseries or distroseries/sourcepackagename must be given
        but not all.

        :param files: A list of paths to the translation files.
        :param productseries: The productseries that this upload is for.
        :param distroseries: The distroseries that this upload is for.
        :param sourcepackagename: The sourcepackagename that this upload
            is for.
        """
        assert((productseries is not None and
                distroseries is None and sourcepackagename is None) or
               (productseries is None and
                distroseries is not None and sourcepackagename is not None))

        self._potemplates = {}
        self._n_matched = 0
        self.is_approval_possible = True

        potemplate_names = set()

        importer = TranslationImporter()
        self._potemplateset = getUtility(IPOTemplateSet).getSubset(
            iscurrent=True, productseries=productseries,
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        for path in files:
            if importer.isTemplateName(path):
                potemplate = self._potemplateset.getPOTemplateByPath(path)
                if potemplate is None:
                    name = self.makeNameFromPath(path)
                    potemplate = self._potemplateset.getPOTemplateByName(name)
                else:
                    name = potemplate.name
                # Template names must occur only once.
                if name in potemplate_names:
                    self.is_approval_possible = False
                else:
                    potemplate_names.add(name)
                if potemplate is not None:
                    self._n_matched += 1
                self._potemplates[path] = potemplate
        # The simplest case of exactly one file and one POTemplate object is
        # always approved.
        if len(self._potemplateset) == len(self._potemplates) == 1:
            self._potemplates[self._potemplates.keys()[0]] = (
                self._potemplateset[0])
            self.is_approval_possible = True

    @property
    def unmatched_objects(self):
        """The number of IPOTemplate objects that are not matched by path
        to a file being imported.
        """
        return len(self._potemplateset)-self._n_matched

    @property
    def unmatched_files(self):
        """The number of files being imported that are not matched by path
        to an IPOTemplate object.
        """
        return len(self._potemplates)-self._n_matched

    @staticmethod
    def makeDomain(path):
        dname, fname = os.path.split(path)
        # Handle generic names and xpi cases
        if fname not in TranslationBranchApprover.GENERIC_TEMPLATE_NAMES:
            return os.path.splitext(fname)[0]
        dname1, dname2 = os.path.split(dname)
        if dname2 not in TranslationBranchApprover.GENERIC_TEMPLATE_DIRS:
            return dname2
        return os.path.split(dname1)[1] # May be empty if dname1 was empty

    @staticmethod
    def makeName(domain):
        """Make a template name from a translation domain."""
        return domain.replace('_', '-')

    @staticmethod
    def makeNameFromPath(path):
        """Make a template name from a file path."""
        return TranslationBranchApprover.makeName(
            TranslationBranchApprover.makeDomain(path))

    def approve(self, entry):
        """Check the given ImportQueueEntry against the internal approval
        list and set its values accordingly.

        :param entry: The queue entry that needs to be approved.
        """
        if not self.is_approval_possible:
            return entry
        potemplate = None
        # Path must provide a translation domain.
        domain = self.makeDomain(entry.path)
        if domain == '':
            return entry
        # Path must be a template path.
        if not self._potemplates.has_key(entry.path):
            return entry

        if self._potemplates[entry.path] is None:
            if self.unmatched_objects > 0:
                # Unmatched entries in database, do not approve.
                return entry
            # No (possibly) matching entry found: create one.
            name = self.makeName(domain)
            potemplate = self._potemplateset.new(
                name, domain, entry.path, entry.importer)
            self._potemplates[entry.path] = potemplate
        else:
            # A matching entry is found, the import can be approved.
            potemplate = self._potemplates[entry.path]
            potemplate.path = entry.path
            potemplate.translation_domain = domain

        # Approve the entry
        entry.potemplate = potemplate
        entry.status = RosettaImportStatus.APPROVED
        return entry

