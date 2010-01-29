#!/usr/bin/python2.6

# This work is licensed under the Creative Commons Attribution 3.0 United
# States License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by/3.0/us/ or send a letter to Creative
# Commons, 171 Second Street, Suite 300, San Francisco, California, 94105, USA.
# Derived from make_master.py by Oran Looney.
# http://oranlooney.com/make-css-sprites-python-image-library/

import os
import Image

MARGIN = 18
OUTPUT_DIR = './pil_sprites'
TEMPLATE_CSS_FILE = 'lib/canonical/launchpad/icing/sprite-template.css'

def get_sprites():
    smartsprites_exp = re.compile(
        r'.*/\*+([^*]*sprite-ref: icon-sprites;[^*]*)\*.*')
    template_css = cssutils.parseFile(TEMPLATE_CSS_FILE)
    sprites = []
    for rule in template_css:
        match = smartsprites_exp.match(rule.cssText)
        if match is not None:
            smartsprites_info = match.group(1)
            for parameter in smartsprites_info.split(';'):
                name, value = parameter.split(':')
                name = name.strip()
                value = value.strip()
                if name == 'icon-sprites':
                    sprites.append(dict(
                        filename=filename,
                        rule=rule))


    return sprites

sprites = get_sprites()

for sprite in sprites:
    sprite['image'] = Image.open(sprite['filename'])

print "%d images will be combined." % len(sprites)

max_width = 0
total_height = 0
for sprite in sprites:
    max_width = max(sprite['image'].width, max_width)
    total_height += sprite['image'].height

master_width = max_width
# Separate each image with lots of whitespace.
master_height = total_height + (MARGIN * len(images))
print "the master image will by %d by %d" % (master_width, master_height)
print "creating image...",
transparent = (0,0,0,0)
master = Image.new(
    mode='RGBA',
    size=(master_width, master_height),
    color=transparent)

print "created."

sprites = []
y = 0
for index, sprite in enumerate(sprites):
    print "adding %s at %d" % (sprite['filename'], sprite['y_position'])
    master.paste(sprite['image'], (0, sprite['y_position']))
    y += sprite['image'].height + MARGIN
print "done adding icons."

print "saving master.gif...",
master.save(os.path.join(OUTPUT_DIR, 'master.gif'), transparency=0)
print "saved!"

print "saving master.png...",
master.save(os.path.join(OUTPUT_DIR, 'master.png'))
print "saved!"


css_template = '''.%s {
    background-image:url(/static/icons/master.%s);
    background-position: 6px %dpx;
}
'''

for format in ['png','gif']:
    print 'saving icons_%s.css...' % format,
    css_filename = os.path.join(OUTPUT_DIR, 'icons_%s.css' % format)
    with open(css_filename,'w') as sprite_css_file:
        for sprite in sprites:
            rule = sprite['rule']
            rule.style.backgroundImage = 'url(master.%s)' % format
            rule.style.backgroundPosition = '0px %dpx' % sprite['y_position']
            sprite_css_file.write(sprite['rule'].cssText)
            sprite_css_file.write('\n')
                css_template
                % (sprite['rule'], format, sprite['y_position']))
    print 'created', css_filename
