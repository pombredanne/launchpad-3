#!/usr/bin/python

import sys
import os
import re

style_exp = re.compile(
    r'\.([a-zA-Z-]*) .*url\(([^)]*-sprites[^)]*)\) ([0-9px-]*).*')

directive_template = (
    "/** sprite: %s; sprite-image: url('new-%s.png'); "
    "sprite-layout: vertical; */")

image_dir = 'lib/canonical/launchpad/images'

def main():
    image_file_util = ImageFileUtil()
    prev_sprite_group = None
    for line in open('lib/canonical/launchpad/icing/style-3-0.css'):
        match = style_exp.match(line)
        if match is not None:
            image_name, sprite_group, offset = match.groups()
            if sprite_group != prev_sprite_group:
                prev_sprite_group = sprite_group
                #print
                #print
                #print directive_template % (sprite_group, sprite_group)
            image_file = image_file_util.add(image_name, sprite_group, offset)
            continue
            print (
                '.%(image)s '
                '{background-image: url(../images/%(image)s.png);} '
                '/** sprite-ref: %(sprite_group)s */'
                % dict(image=image_name, sprite_group=sprite_group))
    print
    image_file_util.reprocess_missing()


class ImageFileUtil:
    def __init__(self):
        self.cache = {}
        self.missing = set()
        self.found = []

    def reprocess_missing(self):
        for args in self.missing:
            image_file = self.add(*args)
            if image_file is None:
                raise AssertionError(
                    "File for css class still not found:", args)

    def add(self, image_name, sprite_group, offset):
        image_file = os.path.join(image_dir, image_name + '.png')
        key = (sprite_group, offset)
        if not os.path.isfile(image_file):
            swapped_image_name = '-'.join(reversed(image_name.split('-')))
            image_file = os.path.join(
                image_dir, swapped_image_name + '.png')
            if not os.path.isfile(image_file):
                if key not in self.cache:
                    self.missing.add((image_name, sprite_group, offset))
                    return
        if key not in self.cache:
            self.cache[key] = image_file
        self.found.append(
            dict(sprite_group=sprite_group,
                 image_file=image_file,
                 css_class=image_name))
        return image_file


if __name__ == '__main__':
    main()
