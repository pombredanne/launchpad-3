#!/usr/bin/python

import sys
import os
import re

style_exp = re.compile(r'\.([a-zA-Z-]*) .*url\(([^)]*-sprites[^)]*)\).*')

directive_template = (
    "/** sprite: %s; sprite-image: url('new-%s.png'); "
    "sprite-layout: vertical; */")

image_dir = 'lib/canonical/launchpad/images'

prev_sprite_group = None
for line in open('lib/canonical/launchpad/icing/style-3-0.css'):
    match = style_exp.match(line)
    if match is not None:
        image_name, sprite_group = match.groups()
        if sprite_group != prev_sprite_group:
            prev_sprite_group = sprite_group
            #print
            #print
            #print directive_template % (sprite_group, sprite_group)
        image_file = os.path.join(image_dir, image_name + '.png')
        if not os.path.isfile(image_file):
            swapped_image_name = '-'.join(reversed(image_name.split('-')))
            swapped_image_file = os.path.join(
                image_dir, swapped_image_name + '.png')
            if not os.path.isfile(swapped_image_file):
                print "Image not found for css class:", image_name
        continue
        print (
            '.%(image)s {background-image: url(../images/%(image)s.png);} '
            '/** sprite-ref: %(sprite_group)s */'
            % dict(image=image_name, sprite_group=sprite_group))

