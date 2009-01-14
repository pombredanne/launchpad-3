# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers for canonical widgets."""

import os


def get_widget_template(filename):
    """Return the content of lib/canonical/widgets/templates/<filename>."""
    here = os.path.dirname(__file__)
    template_path = os.path.join(here, 'templates', filename)
    file = open(template_path)
    try:
        return file.read()
    finally:
        file.close()
