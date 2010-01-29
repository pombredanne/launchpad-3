#!/usr/bin/python2.5

# This work is licensed under the Creative Commons Attribution 3.0 United
# States License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by/3.0/us/ or send a letter to Creative
# Commons, 171 Second Street, Suite 300, San Francisco, California, 94105, USA.
# Derived from make_master.py by Oran Looney.
# http://oranlooney.com/make-css-sprites-python-image-library/

from __future__ import with_statement
import os
import sys
import re
import cssutils
import Image

MARGIN = 18
OUTPUT_DIR = './pil_sprites'
TEMPLATE_CSS_FILE = 'lib/canonical/launchpad/icing/sprite-template.css'

def get_sprites():
    smartsprites_exp = re.compile(
        r'/\*+([^*]*sprite-ref: icon-sprites;[^*]*)\*')
    template_css = cssutils.parseFile(TEMPLATE_CSS_FILE)
    sprites = []
    for rule in template_css:
        match = smartsprites_exp.search(rule.cssText)
        if match is not None:
            smartsprites_info = match.group(1)
            for parameter in smartsprites_info.split(';'):
                if parameter.strip() != '':
                    name, value = parameter.split(':')
                    name = name.strip()
                    value = value.strip()
                    if value == 'icon-sprites':
                        # Remove url() from string.
                        filename = rule.style.backgroundImage[4:-1]
                        sprites.append(dict(filename=filename, rule=rule))
    return sprites

sprites = get_sprites()

for sprite in sprites:
    css_dir, _css_file = os.path.split(TEMPLATE_CSS_FILE)
    filename = os.path.join(css_dir, sprite['filename'])
    sprite['image'] = Image.open(filename)

if len(sprites) == 0:
    print >> sys.stderr, "No images found."
    sys.exit(1)
print "%d images will be combined." % len(sprites)

max_width = 0
total_height = 0
for sprite in sprites:
    width, height = sprite['image'].size
    max_width = max(width, max_width)
    total_height += height

master_width = max_width
# Separate each image with lots of whitespace.
master_height = total_height + (MARGIN * len(sprites))
print "the master image will be %d by %d" % (master_width, master_height)
transparent = (0,0,0,0)
master = Image.new(
    mode='RGBA',
    size=(master_width, master_height),
    color=transparent)

y = 0
for index, sprite in enumerate(sprites):
    print "adding %s at %d" % (sprite['filename'], y)
    master.paste(sprite['image'], (0, y))
    sprite['y_position'] = y
    y += sprite['image'].size[1] + MARGIN
print "done adding icons."

print "saving master.gif...",
master.save(os.path.join(OUTPUT_DIR, 'master.gif'), transparency=0)
print "saved!"

print "saving master.png...",
master.save(os.path.join(OUTPUT_DIR, 'master.png'))
print "saved!"


for format in ['png','gif']:
    css_filename = os.path.join(OUTPUT_DIR, 'icons_%s.css' % format)
    print 'saving', css_filename
    with open(css_filename,'w') as sprite_css_file:
        for sprite in sprites:
            rule = sprite['rule']
            rule.style.backgroundImage = 'url(master.%s)' % format
            rule.style.backgroundPosition = '0px %dpx' % sprite['y_position']
            sprite_css_file.write(sprite['rule'].cssText)
            sprite_css_file.write('\n')
