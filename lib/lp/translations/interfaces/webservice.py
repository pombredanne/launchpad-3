# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0611

"""All the interfaces that are exposed through the webservice."""

__all__ = [
    'IHasTranslationImports',
    'IPOFile',
    'IPOTemplate',
    'ITranslationImportQueue',
    'ITranslationImportQueueEntry',
    ]

from lp.translations.interfaces.pofile import IPOFile
from lp.translations.interfaces.potemplate import IPOTemplate
from lp.translations.interfaces.translationimportqueue import (
    IHasTranslationImports,
    ITranslationImportQueue,
    ITranslationImportQueueEntry,
    )


