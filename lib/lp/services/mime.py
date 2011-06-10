# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Methods required to customize the mimetypes library."""

__metaclass__ = type
__all__ = [
    'customizeMimetypes',
    ]

import mimetypes


def customizeMimetypes():
    """Initialize and extend the standard mimetypes library for our needs.

    This method is to be called before any requests are processed to ensure
    any call site that imports the standard mimetypes module will take
    advantage of these customizations.
    """
    mimetypes.init()

    # Add support for bz2 encodings, which is not present in python2.5.
    mimetypes.encodings_map.setdefault('.bz2', 'bzip2')
    mimetypes.encodings_map.setdefault('.bzip2', 'bzip2')
    mimetypes.suffix_map.setdefault('.tbz2', '.tar.bz2')

    # XXX: GavinPanella 2008-07-04 bug=229040: A fix has been requested
    # for Intrepid, to add .debdiff to /etc/mime.types, so we may be able
    # to remove this setting once a new /etc/mime.types has been installed
    # on the app servers. Additionally, Firefox does not display content
    # of type text/x-diff inline, so making this text/plain because
    # viewing .debdiff inline is the most common use-case.
    mimetypes.add_type('text/plain', '.debdiff')

    # Add support for Launchpad's OWL decription of its RDF metadata.
    mimetypes.add_type('application/rdf+xml', '.owl')
