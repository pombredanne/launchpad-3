# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.launchpad.windmill.testing import (
    lpuser,
    widgets,
    )
from lp.soyuz.windmill.testing import SoyuzWindmillLayer


class TestPPAInlineEditing(unittest.TestCase):
    """Ensure that various inline editing on the PPA page work."""

    layer = SoyuzWindmillLayer

    def test_ppa_displayname_inline_edit(self):
        """Ensure the PPA dispalyname can be edited inline."""

        ppa_displayname_inline_edit_test = widgets.InlineEditorWidgetTest(
            url='%s/~cprov/+archive/ppa' % SoyuzWindmillLayer.base_url,
            widget_id='displayname',
            expected_value='PPA for Celso Providelo',
            new_value="Celso's default PPA",
            name='test_ppa_displayname_inline_edit',
            user=lpuser.FOO_BAR,
            suite=__name__)

        ppa_displayname_inline_edit_test()
