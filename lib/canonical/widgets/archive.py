# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Widgets related to `IArchive`."""

__metaclass__ = type
__all__ = [
    'PPANameWidget',
    ]

import urlparse

from z3c.ptcompat import ViewPageTemplateFile

from canonical.config import config
from canonical.widgets.textwidgets import LowerCaseTextWidget


class PPANameWidget(LowerCaseTextWidget):
    """A text input widget that looks like a URL path component entry."""
    template = ViewPageTemplateFile('templates/ppa-url.pt')

    def __call__(self):
        return self.template()

    @property
    def base_url(self):
        field = self.context
        owner = field.context
        if owner.private:
            root = config.personalpackagearchive.private_base_url
        else:
            root = config.personalpackagearchive.base_url
        return urlparse.urljoin(root, owner.name)

    @property
    def archive_name(self):
        return self._getFormValue().lower()
