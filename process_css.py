#!/usr/bin/python

import sys
import os
import re

style_exp = re.compile(
    r'\.([a-zA-Z-]*) .*url\(([^)]*-sprites[^)]*)\) ([0-9px-]*).*')

directive_template = (
    "/** sprite: %(sprite_group)s; "
    "sprite-image: url('new-%(sprite_group)s.png'); "
    "sprite-layout: vertical; */")

image_dir = 'lib/canonical/launchpad/images'

def main():
    image_file_util = ImageFileUtil()
    for line in open('lib/canonical/launchpad/icing/style-3-0.css'):
        match = style_exp.match(line)
        if match is not None:
            css_class, sprite_group, offset = match.groups()
            image_file_util.add(css_class, sprite_group, offset)
    print
    image_file_util.reprocessMissing()
    print_css(image_file_util)

def get_css_info_key(css):
    return (css['sprite_group'], css['css_class'])

def print_css(image_file_util):
    prev_sprite_group = None
    for css in sorted(image_file_util.found, key=get_css_info_key):
        if css['sprite_group'] != prev_sprite_group:
            prev_sprite_group = css['sprite_group']
            print
            print
            print directive_template % css
            print
        _head, image_file = os.path.split(css['image_path'])
        css = css.copy()
        css['image_file'] = image_file
        print (
            '.%(css_class)s '
            '{background-image: url(../images/%(image_file)s);} '
            '/** sprite-ref: %(sprite_group)s */'
            % css)


class ImageFileUtil:
    def __init__(self):
        self.cache = {}
        self.missing = set()
        self.found = []

    def reprocessMissing(self):
        for args in self.missing:
            image_path = self.add(*args)
            if image_path is None:
                raise AssertionError(
                    "File for css class still not found:", args)

    def add(self, css_class, sprite_group, offset):
        image_path = os.path.join(image_dir, css_class + '.png')
        key = (sprite_group, offset)
        if not os.path.isfile(image_path):
            swapped_image_name = '-'.join(reversed(css_class.split('-')))
            image_path = os.path.join(
                image_dir, swapped_image_name + '.png')
            if not os.path.isfile(image_path):
                if key not in self.cache:
                    self.missing.add((css_class, sprite_group, offset))
                    return
        if key not in self.cache:
            self.cache[key] = image_path
        self.found.append(
            dict(sprite_group=sprite_group,
                 image_path=image_path,
                 css_class=css_class))
        return image_path


if __name__ == '__main__':
    main()
