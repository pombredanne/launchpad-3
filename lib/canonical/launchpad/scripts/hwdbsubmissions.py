# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Parse HWDB submissions.

Base classes, intended to be used both for the commercial cerfitication
data and for the community test submissions.
"""

__all__ = ['SubmissionParser']

from logging import getLogger
from lxml import etree
import os

from canonical.config import config

_relax_ng_files = {
    '1.0': 'hardware-1_0.rng'}

class SubmissionParser:
    """A Parser for the submissions to the hardware database."""

    def __init__(self, logger=None):
        """Create a new ProcessNewSubmissions instance."""
        if logger is None:
            logger = getLogger()
        self.logger = logger
        self.doc_parser = etree.XMLParser(remove_comments=True)

        self.validator = {}
        for version, relax_ng_filename in _relax_ng_files.items():
            path = (config.root, 'lib', 'canonical', 'launchpad', 'scripts')
            path = path + (relax_ng_filename, )
            path = os.path.join(*path)
            relax_ng_doc = etree.parse(path)
            self.validator[version] = etree.RelaxNG(relax_ng_doc)

    def log_error(self, message, submission_key):
        self.logger.error(
            'Parsing submission %s: %s' % (submission_key, message))

    def validatedEtree(self, submission, submission_key):
        """Validate the XML string `submission`.

        Return an lxml.etree instance representation of a valid submission
        or None for invalid submissions.
        """
        try:
            submission_doc = etree.fromstring(
                submission, parser=self.doc_parser)
        except etree.XMLSyntaxError, error_value:
            self.log_error(error_value, submission_key)
            return None

        if submission_doc.tag != 'system':
            self.log_error("root node is not '<system>'", submission_key)
            return None
        version = submission_doc.attrib.get('version', None)
        if not version in self.validator.keys():
            self.log_error(
                'invalid submission format version: %s' % repr(version),
                submission_key)
            return None
        self.submission_format_version = version

        validator = self.validator[version]
        if not validator(submission_doc):
            self.log_error(
                'Relax NG validation failed.\n%s' % validator.error_log,
                submission_key)
            return None
        return submission_doc
