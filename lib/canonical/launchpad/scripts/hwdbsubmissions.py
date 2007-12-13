# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Parse Hardware Database submissions.

Base classes, intended to be used both for the commercial certification
data and for the community test submissions.
"""

__all__ = ['SubmissionParser']

from logging import getLogger
from lxml import etree
import os

from canonical.config import config


_relax_ng_files = {
    '1.0': 'hardware-1_0.rng', }


class SubmissionParser:
    """A Parser for the submissions to the hardware database."""

    def __init__(self, logger=None):
        if logger is None:
            logger = getLogger()
        self.logger = logger
        self.doc_parser = etree.XMLParser(remove_comments=True)

        self.validator = {}
        directory = os.path.join(config.root, 'lib', 'canonical',
                                 'launchpad', 'scripts')
        for version, relax_ng_filename in _relax_ng_files.items():
            path = os.path.join(directory, relax_ng_filename)
            relax_ng_doc = etree.parse(path)
            self.validator[version] = etree.RelaxNG(relax_ng_doc)

    def _logError(self, message, submission_key):
        self.logger.error(
            'Parsing submission %s: %s' % (submission_key, message))

    def _getValidatedEtree(self, submission, submission_key):
        """Create an etree doc from the XML string submission and validate it.

        :return: an `lxml.etree` instance representation of a valid
            submission or None for invalid submissions.
        """
        try:
            submission_doc = etree.fromstring(
                submission, parser=self.doc_parser)
        except etree.XMLSyntaxError, error_value:
            self._logError(error_value, submission_key)
            return None

        if submission_doc.tag != 'system':
            self._logError("root node is not '<system>'", submission_key)
            return None
        version = submission_doc.attrib.get('version', None)
        if not version in self.validator.keys():
            self._logError(
                'invalid submission format version: %s' % repr(version),
                submission_key)
            return None
        self.submission_format_version = version

        validator = self.validator[version]
        if not validator(submission_doc):
            self._logError(
                'Relax NG validation failed.\n%s' % validator.error_log,
                submission_key)
            return None
        return submission_doc
