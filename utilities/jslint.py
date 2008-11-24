#!/usr/bin/python2.4
"""jslint.py - run the JSLint linter on all input files."""

__metaclass__ = type
__all__ = []

import os
import subprocess
import sys


JS = '/usr/bin/js'
FULLJSLINT= os.path.join(os.path.dirname(__file__), 'fulljslint.js')


def jslint(filename):
    """Run the JSLint script on the filename."""
    jsfile = file(filename, 'r')
    # JavaScript cannot read files directly. So we define the JSLint driver
    # here and pipe the file content through stdin. 
    command = [JS, '-e', r'''
        load('%(fulljslint)s');

        /* We use our custom reporting instead of JSLint.report() which
           outputs HTML. */
        function print_implied_names() {
            /* Report about implied global names. */
            var implied_names = [], name;
            for (name in JSLINT.implied) {
                implied_names.push(name);
            }

            if (implied_names.length > 0 ) {
                print('Implied globals:');
                implied_names.sort();
                print(implied_names.join(', '));
                print('\n');
            }
        }

        function print_lint_errors() {
            /* Report about lint errors. */
            for (var i=0; i < JSLINT.errors.length; i++) {
                var error = JSLINT.errors[i];
                if (!error) //It seems that this is possible :-(
                    continue;
                var line_no = error.line + 1;
                var char_no = error.character + 1;
                print(
                    'Line ' + line_no + ' character ' + char_no + ': ' +
                    error.reason);
                if (error.evidence) {
                    print(error.evidence);
                }
                print('\n');
            }
        }

        /* Since readline() doesn't distinguish between an empty line
           and a EOF, we use an EOF marker. */
        var content = '', line = '';
        while (line != 'EOF') {
           content += line + '\n';
           line = readline()
        }

        JSLINT(content);

        var error_count = JSLINT.errors.length;
        if (JSLINT.implied) {
            error_count +=1;
        }
        if (error_count > 0) {
            print(error_count + ' lint problems found in %(filename)s:\n');
            print_implied_names();
            print_lint_errors();
        } else {
            print('No lint in %(filename)s');
        }
        ''' % dict(
            fulljslint=FULLJSLINT, filename=os.path.basename(filename))]
    js = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=None, stderr=subprocess.STDOUT)
    js.stdin.write(jsfile.read())
    js.stdin.write('EOF\n')
    return js.wait()


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        jslint(filename)
