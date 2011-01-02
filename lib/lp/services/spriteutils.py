# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Derived from make_master.py by Oran Looney.
# http://oranlooney.com/make-css-sprites-python-image-library/

"""Library to create sprites."""

__metaclass__ = type

__all__ = [
    'SpriteUtil',
    ]

import os
import re
import sys
from textwrap import dedent

import cssutils
import Image
import simplejson


class SpriteUtil:
    EDIT_WARNING = dedent("""\
        /* DO NOT EDIT THIS FILE BY HAND!!!    */
        /* It is autogenerated by spriteutils. */
        """)

    def __init__(self, css_template_file, group_name,
                 url_prefix_substitutions=None, margin=150):
        """Initialize with the specified css template file.

        :param css_template_file: (str) Name of the file containing
            css rules with a background-image style that needs to be
            combined into the sprite file, a comment allowing sprites to
            be grouped into different image files, and a
            background-repeat style if necessary. Currently, "repeat-y"
            is not supported since the file is combined vertically, so
            repeat-y would show the entire combined image file.

            Example css template:
                edit-icon {
                    background-image: url(../edit.png)
                    /* sprite-ref: group1 */
                }
                blue-bar {
                    background-image: url(../blue-bar.png)
                    /* sprite-ref: group1 */
                    background-repeat: repeat-x
                }

        :param group_name: (str) Only add sprites to the
            combined image file whose sprite-ref comment in the
            css template match this group-name.

        :param url_prefix_substitutions: (dict) The css template
            will contain references to image files by their url
            path, but the filesystem path relative to the css
            template is needed.

        :param margin: (int) The number of pixels between each sprite.
            Be aware that Firefox will ignore extremely large images,
            for example 64x34000 pixels.

        If the css_template_file has been modified, a new
        css file using an existing combined image and positioning
        file can be generated using:
            sprite_util = SpriteUtil(...)
            sprite_util.loadPositioning(...)
            sprite_util.saveConvertedCSS(...)

        If a new image file needs to be added to the combined image
        and the positioning file, they can be regenerated with:
            sprite_util = SpriteUtil(...)
            sprite_util.combineImages(...)
            sprite_util.savePNG(...)
            sprite_util.savePositioning(...)

        If the image file is regenerated any time the css file is
        regenerated, then the step for saving and loading the positioning
        information could be removed. For example:
            sprite_util = SpriteUtil(...)
            sprite_util.combineImages(...)
            sprite_util.savePNG(...)
            sprite_util.saveConvertedCSS(...)
        """
        self.combined_image = None
        self.positions = None
        self.group_name = group_name
        self.margin = margin
        self._loadCSSTemplate(
            css_template_file, group_name, url_prefix_substitutions)

    def _loadCSSTemplate(self, css_template_file, group_name,
                        url_prefix_substitutions=None):
        """See `__init__`."""
        smartsprites_exp = re.compile(
            r'/\*+([^*]*sprite-ref: [^*]*)\*/')
        self.css_object = cssutils.parseFile(css_template_file)
        self.sprite_info = []
        for rule in self.css_object:
            if rule.cssText is None:
                continue
            match = smartsprites_exp.search(rule.cssText)
            if match is not None:
                smartsprites_info = match.group(1)
                parameters = self._parseCommentParameters(match.group(1))
                # Currently, only a single combined image is supported.
                if parameters['sprite-ref'] == group_name:
                    filename = self._getSpriteImagePath(
                        rule, url_prefix_substitutions)
                    if filename == '':
                        raise AssertionError(
                            "Missing background-image url for %s css style"
                            % rule.selectorText)
                    self.sprite_info.append(
                        dict(filename=filename, rule=rule))

        if len(self.sprite_info) == 0:
            raise AssertionError(
                "No sprite-ref comments for group %r found" % group_name)

    def _getSpriteImagePath(self, rule, url_prefix_substitutions=None):
        """Convert the url path to a filesystem path."""
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
        """Parse parameters out of javascript comments.

        Currently only used for the group name specified
        by "sprite-ref".
        """
        results = {}
        for parameter in parameter_string.split(';'):
            if parameter.strip() != '':
                name, value = parameter.split(':')
                name = name.strip()
                value = value.strip()
                results[name] = value
        return results

    def combineImages(self, css_dir):
        """Copy all the sprites into a single PIL image."""

        # Open all the sprite images.
        sprite_images = {}
        max_sprite_width = 0
        total_sprite_height = 0
        for sprite in self.sprite_info:
            abs_filename = os.path.join(css_dir, sprite['filename'])
            try:
                sprite_images[sprite['filename']] = Image.open(abs_filename)
            except IOError:
                print >> sys.stderr, "Error opening '%s' for %s css rule" % (
                    abs_filename, sprite['rule'].selectorText)
                raise
            width, height = sprite_images[sprite['filename']].size
            max_sprite_width = max(width, max_sprite_width)
            total_sprite_height += height

        # The combined image is the height of all the sprites
        # plus the margin between each of them.
        combined_image_height = (
            total_sprite_height + (self.margin * len(self.sprite_info) - 1))
        transparent = (0, 0, 0, 0)
        combined_image = Image.new(
            mode='RGBA',
            size=(max_sprite_width, combined_image_height),
            color=transparent)

        # Paste each sprite into the combined image.
        y = 0
        positions = {}
        for index, sprite in enumerate(self.sprite_info):
            sprite_image = sprite_images[sprite['filename']]
            try:
                position = [0, y]
                combined_image.paste(sprite_image, tuple(position))
                # An icon in a vertically combined image can be repeated
                # horizontally, but we have to repeat it in the combined
                # image so that we don't repeat white space.
                if sprite['rule'].style.backgroundRepeat == 'repeat-x':
                    width = sprite_image.size[0]
                    for x_position in range(width, max_sprite_width, width):
                        position[0] = x_position
                        combined_image.paste(sprite_image, tuple(position))
            except:
                print >> sys.stderr, (
                    "Error with image file %s" % sprite['filename'])
                raise
            # This is the position of the combined image on an HTML
            # element. Therefore, it subtracts the position of the
            # sprite in the file to move it to the top of the element.
            positions[sprite['filename']] = (0, -y)
            y += sprite_image.size[1] + self.margin

        # If there is an exception earlier, these attributes will remain None.
        self.positions = positions
        self.combined_image = combined_image

    def savePNG(self, filename):
        """Save the PIL image object to disk."""
        self.combined_image.save(filename, format='png', optimize=True)

    def savePositioning(self, filename):
        """Save the positions of sprites in the combined image.

        This allows the final css to be generated after making
        changes to the css template without recreating the combined
        image file.
        """
        fp = open(filename, 'w')
        fp.write(self.EDIT_WARNING)
        simplejson.dump(self.positions, fp=fp, indent=4)

    def loadPositioning(self, filename):
        """Load file with the positions of sprites in the combined image."""
        json = open(filename).read()
        # Remove comments from the beginning of the file.
        start = json.index('{')
        json = json[start:]
        self.positions = simplejson.loads(json)

    def saveConvertedCSS(self, css_file, combined_image_url_path):
        """Generate new css from the template and the positioning info.

        Example css template:
            background-image: url(../edit.png); /* sprite-ref: group1 */
        Example css output:
            background-image: url(combined_image_url_path)
            background-position: 0px 2344px
        """
        for sprite in self.sprite_info:
            rule = sprite['rule']
            rule.style.backgroundImage = 'url(%s)' % combined_image_url_path
            position = self.positions[sprite['filename']]
            rule.style.backgroundPosition = '%dpx %dpx' % tuple(position)

        with open(css_file, 'w') as fp:
            fp.write(self.EDIT_WARNING)
            fp.write(self.css_object.cssText)
