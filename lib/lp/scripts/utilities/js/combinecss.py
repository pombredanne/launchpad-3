# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

from lp.scripts.utilities.js.jsbuild import ComboFile
from lp.scripts.utilities.js.combo import combine_files
from lp.services.config import config


# It'd probably be nice to have this script find all the CSS files we might
# need and combine them together, but if we do that we'd certainly end up
# including lots of styles that we don't need/want, so keeping this hard-coded
# list seems like the best option for now.
names = [
    'ubuntu-webfonts.css',
    'style.css',
    'yui/cssreset/cssreset.css',
    'yui/calendar-base/assets/skins/sam/calendar-base.css',
    'yui/calendar/assets/skins/sam/calendar.css',
    'yui/calendarnavigator/assets/skins/sam/calendarnavigator.css',
    # Since the old cssgrids uses yui-, and the new uses yui3-, it is only
    # used for the calendar.
    'yui/cssgrids/cssgrids.css',
    # Use the old cssgrids instead of the new cssgrids.
    'cssgrids/grids.css',
    'build/ui/assets/skins/sam/lazr.css',
    'build/ui/assets/skins/sam/banner.css',
    'build/inlineedit/assets/skins/sam/editor.css',
    'build/autocomplete/assets/skins/sam/autocomplete.css',
    'build/overlay/assets/skins/sam/pretty-overlay.css',
    'build/formoverlay/assets/formoverlay-core.css',
    'build/inlinehelp/assets/inlinehelp-core.css',
    'build/indicator/assets/indicator-core.css',
    'build/confirmationoverlay/assets/confirmationoverlay-core.css',
    'build/picker/assets/skins/sam/picker.css',
    'build/activator/assets/skins/sam/activator.css',
    'build/choiceedit/assets/choiceedit-core.css',
    'build/ordering/assets/ordering-core.css',
    'build/gallery-accordion/assets/gallery-accordion-core.css',
    'build/gallery-accordion/assets/skins/sam/gallery-accordion-skin.css',
    'build/inline-sprites-1.css',
    'build/inline-sprites-2.css',
    'build/block-sprites-1.css',
    # Include our main stylesheets at the end so they
    # take precedence over the others.
    'css/base.css',
    'css/typography.css',
    'css/colours.css',
    'css/forms.css',
    'css/layout.css',
    'css/modifiers.css']


def main():
    icing = os.path.join(config.root, 'lib/canonical/launchpad/icing')
    target = os.path.join(icing, 'combo.css')

    # Get all the component css files so we don't have to edit this file
    # every time a new component is added.
    component_dir = 'css/components'
    component_path = os.path.abspath(os.path.join(icing, component_dir))
    for root, dirs, files in os.walk(component_path):
        for file in files:
            if file.endswith('.css'):
                names.append('%s/%s' % (component_dir, file))

    absolute_names = []
    for name in names:
        full_path_name = os.path.abspath(os.path.join(icing, name))
        absolute_names.append(full_path_name)

    combo = ComboFile(absolute_names, target)
    if combo.needs_update():
        result = ''
        for content in combine_files(names, icing):
            result += content

        with open(target, 'w') as f:
            f.write(result)
