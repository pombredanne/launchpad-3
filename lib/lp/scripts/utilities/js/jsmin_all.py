#!/usr/bin/env python

"""Handle minifying all javascript files in the build directory by walking

$ jsmin_all.py $lp_js_root

"""
import os
import re
import sys
from jsmin import JavascriptMinify


def dirwalk(dir):
    "walk a directory tree, using a generator"
    for f in os.listdir(dir):
        fullpath = os.path.join(dir,f)
        if os.path.isdir(fullpath) and not os.path.islink(fullpath):
            for x in dirwalk(fullpath):  # recurse into subdir
                yield x
        else:
            yield fullpath


def minify(filename):
    """Given a filename, handle minifying it as -min.js"""
    if not re.search("^(min).js$", filename):
        new_filename = re.sub(".js$", "-min.js", filename)

        with open(filename) as shrink_me:
            with open(new_filename, 'w') as tobemin:
                jsm = JavascriptMinify()
                jsm.minify(shrink_me, tobemin)


if __name__ == '__main__':
    root_dir = sys.argv[1]
    [minify(f) for f in dirwalk(root_dir)]
