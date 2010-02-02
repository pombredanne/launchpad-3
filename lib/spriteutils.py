# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Derived from make_master.py by Oran Looney.
# http://oranlooney.com/make-css-sprites-python-image-library/

"""Library to create sprites."""

from __future__ import with_statement

__metaclass__ = type

__all__ = [
    'SpriteUtil',
    ]

import os
import sys
import re
import cssutils
import Image
import simplejson

MARGIN = 18

class SpriteUtil:
    def __init__(self):
        self.sprites = None
        self.combined_image = None
        self.positions = None
        self.css_object = None

    def loadCSSTemplate(self, css_file, group_name,
                        url_prefix_substitutions=None):
        smartsprites_exp = re.compile(
            r'/\*+([^*]*sprite-ref: [^*]*)\*/')
        self.css_object = cssutils.parseFile(css_file)
        sprites = []
        for rule in self.css_object:
            if rule.cssText is None:
                continue
            match = smartsprites_exp.search(rule.cssText)
            if match is not None:
                smartsprites_info = match.group(1)
                parameters = self._parseCommentParameters(match.group(1))
                if parameters['sprite-ref'] == group_name:
                    filename = self._getSpriteImagePath(
                        rule, url_prefix_substitutions)
                    sprites.append(dict(filename=filename, rule=rule))
        self.sprites = sprites
        self.group_name = group_name

    def _getSpriteImagePath(self, rule, url_prefix_substitutions=None):
        # Remove url() from string.
        filename = rule.style.backgroundImage[4:-1]
        # Convert urls to paths relative to the css
        # file, e.g. '/@@/foo.png' => '../images/foo.png'.
        if url_prefix_substitutions is not None:
            for old, new in url_prefix_substitutions.items():
                if filename.startswith(old):
                    filename = new + filename[len(old):]
        return filename

    def _parseCommentParameters(self, parameter_string):
        results = {}
        for parameter in parameter_string.split(';'):
            if parameter.strip() != '':
                name, value = parameter.split(':')
                name = name.strip()
                value = value.strip()
                results[name] = value
        return results

    def combineImages(self, css_dir):
        for sprite in self.sprites:
            filename = os.path.join(css_dir, sprite['filename'])
            sprite['image'] = Image.open(filename)

        if len(self.sprites) == 0:
            raise AssertionError("No images found.")

        max_width = 0
        total_height = 0
        for sprite in self.sprites:
            width, height = sprite['image'].size
            max_width = max(width, max_width)
            total_height += height

        master_width = max_width
        # Separate each image with lots of whitespace.
        master_height = total_height + (MARGIN * len(self.sprites))
        transparent = (0,0,0,0)
        master = Image.new(
            mode='RGBA',
            size=(master_width, master_height),
            color=transparent)

        y = 0
        positions = {}
        for index, sprite in enumerate(self.sprites):
            master.paste(sprite['image'], (0, y))
            # This is the position of the combined image on an HTML
            # element. Therefore, it subtracts the position of the
            # sprite in the file to move it to the top of the element.
            positions[sprite['filename']] = (0, -y)
            y += sprite['image'].size[1] + MARGIN

        self.positions = positions
        self.combined_image = master

    def savePNG(self, filename):
        self.combined_image.save(filename, format='png')

    def savePositioning(self, filename):
        simplejson.dump(self.positions, fp=open(filename, 'w'), indent=4)

    def loadPositioning(self, filename):
        self.positions = simplejson.load(open(filename))

    def saveConvertedCSS(self, css_file, combined_image_file):
        for sprite in self.sprites:
            rule = sprite['rule']
            rule.style.backgroundImage = 'url(%s)' % combined_image_file
            position = self.positions[sprite['filename']]
            rule.style.backgroundPosition = '%dpx %dpx' % tuple(position)

        open(css_file, 'w').write(self.css_object.cssText)
