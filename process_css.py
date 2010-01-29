#!/usr/bin/python

import sys
import os
import re

style_exp = re.compile(
    r'\.([a-zA-Z-]*) .*url\(([^)]*-sprites[^)]*)\) '
    r'([0-9px-]+ [0-9px-]+) (.*);}')

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
            css_class, sprite_group, offset, repeat = match.groups()
            image_file_util.add(css_class, sprite_group, offset, repeat)
        elif '-sprites' in line:
            print 'NOT quite matching:', line
    print
    image_file_util.reprocessMissing()
    print_css(image_file_util)

def get_css_info_key(css):
    #return (css['sprite_group'], css['css_class'])
    #return css['order']
    y_offset = css['offset'].split()[1]
    y_offset = y_offset.strip('px')
    return (css['sprite_group'], -int(y_offset))

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
        if css['css_class'] == 'build-superseded':
            print """.merge-proposal {
  background-image: url(../images/merge-proposal-icon.png); /** sprite-ref: icon-sprites-3; sprite-margin-bottom: 18; */
  background-repeat: no-repeat;
  padding-left: 22px
}"""
        sys.stdout.write(
            '.%(css_class)s '
            '{\n  background-image: url(../images/%(image_file)s); '
            '/** sprite-ref: %(sprite_group)s; '
            'sprite-margin-bottom: 18; '
            % css)
        if css['repeat'] == 'no-repeat':
            print '*/\n  background-repeat: no-repeat;\n}'
        elif css['repeat'] == 'repeat-x':
            print 'sprite-alignment: repeat; */'
            print '  background-repeat: no-repeat;\n}'
        else:
            raise AssertionError(
                "Unhandled background-repeat: %r" % css['repeat'])


class ImageFileUtil:
    def __init__(self):
        self.cache = {}
        self.missing = set()
        self.found = []
        self.order_counter = 0

    def reprocessMissing(self):
        for args in self.missing:
            print "Reprocessing:", args
            image_path = self.add(*args)
            if image_path is None:
                raise AssertionError(
                    "File for css class still not found:", args)

    def add(self, css_class, sprite_group, offset, repeat, order=None):
        if order is None:
            self.order_counter += 1
            order = self.order_counter
        image_path = os.path.join(image_dir, css_class + '.png')
        key = (sprite_group, offset)
        if not os.path.isfile(image_path):
            possible_names = []

            # Remove the hyphen if it exists. Either way,
            # try adding some extensions.
            without_hyphen = css_class.replace('-', '')
            possible_names.append(without_hyphen)
            if '-large' in sprite_group:
                possible_names.append(without_hyphen + '-large')
            elif '-logo' in sprite_group:
                possible_names.append(without_hyphen + '-logo')
            else:
                possible_names.append(without_hyphen + '-icon')

            # Special cases.
            if css_class == 'favorite-yes':
                possible_names.append('news')
            elif css_class == 'external-link':
                possible_names.append('link')
            elif css_class == 'translate-icon':
                possible_names.append('translation')
            elif css_class == 'undecided':
                possible_names.append('maybe')
            elif '-' in css_class:
                # If the css class looks like "foo-bar", try finding
                # a file named "bar-foo.png".
                reversed_name = '-'.join(reversed(css_class.split('-')))
                possible_names.append(reversed_name)
                possible_names.append('person-' + reversed_name)
                possible_names.append('merge-' + reversed_name)

                # Remove last section.
                truncated_name = css_class.rsplit('-', 1)[0]
                possible_names.append(truncated_name)
                possible_names.append(truncated_name + '-icon')
            else:
                # If the css class looks like "foobar", try finding a
                # file named "f-oobar", "fo-obar", "foo-bar", etc.
                for i in range(1, len(css_class)):
                    image_file = css_class[:i] + '-' + css_class[i:]
                    possible_names.append(image_file)


            for image_file in possible_names:
                image_path = os.path.join(image_dir, image_file + '.png')
                if os.path.isfile(image_path):
                    break
            if not os.path.isfile(image_path):
                self.missing.add(
                    (css_class, sprite_group, offset, repeat, order))
                return
        if key not in self.cache:
            self.cache[key] = image_path
        self.found.append(
            dict(sprite_group=sprite_group,
                 image_path=image_path,
                 css_class=css_class,
                 repeat=repeat,
                 offset=offset,
                 order=order))
        return image_path


if __name__ == '__main__':
    main()
