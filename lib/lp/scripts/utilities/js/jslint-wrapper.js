// Copyright (c) 2008
// JSLint wrapper.
//
// Can be run using Rhino using:
// rhino -f ../lib/fulljslint.js jslint-wrapper.js ...
// or Spidermonkey:
// js -f ../lib/fulljslint.js jslint-wrapper.js ...
//
// But Spidermonkey needs special support to emulate readFile.

// This file assumes the fulljslint.js was loaded.
if (typeof(JSLINT) == 'undefined') {
    print('jslint.js: fulljslint.js should be loaded.');
    quit(1);
}

function print_help_and_quit(status) {
    print('jslint [-o options_file] file.js ...');
    print('       -h');
    print('Run linter on all input Javascript files.');
    print('Options:');
    print('    -h               Print this help message and exits');
    print('    --help');
    print();
    print('    -o file          Read file as a JSON object specifing options');
    print('    --options file   to the parser.');
    quit(status);
}

//SpiderMonkey doesn't have a readFile by default.
//We emulate one by PIPING in the content on STDIN with EOF markers.
if (typeof(readFile) == 'undefined') {
    var readFile = function readFile(filename) {
        var content = '', line = '';
        while (line != 'EOF') {
           content += line + '\n';
           line = readline();
        }
        return content;
    };
}

function get_options_file(filename) {
    try {
        var input = readFile(filename);
        if (!input) {
            print("jslint: Couldn't open options file '" + filename + "'.");
            quit(1);
        }
        return eval("x = " + input);
    } catch (e) {
        print("jslint: Error reading options file:");
        print(e);
        quit(1);
    }
}

function get_opt(args) {
    var config = {options: {}, files: []};
    while (args.length > 0) {
        var arg = args.shift();
        switch (arg) {
        case '-o':
        case '--options':
            if (!args.length) {
                print("jslint: Missing options argument");
                print_help_and_quit(1);
            }
            config.options = get_options_file(args.shift());
            break;
        case '-h':
        case '--help':
            print_help_and_quit(0);
            break;
        default:
            if (arg[0] == '-') {
                print('jslint: Unknown option: ' + arg);
                print_help_and_quit(1);
            } else {
                config.files.push(arg);
            }
            break;
        }
    }
    config.files.concat(args);
    return config;
}

/* We use our custom reporting instead of JSLint.report() which
   outputs HTML. */
function print_implied_names() {
    /* Report about implied global names. */
    var implied_names = [], name;
    for (name in JSLINT.implied) {
        if (JSLINT.implied.hasOwnPropery(name)) {
            implied_names.push(name);
        }
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
        if (!error) {
            //It seems that this is possible :-(
            continue;
        }
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

function main(args) {
    config = get_opt(args);
    if (!config.files.length) {
        print('jslint: Missing files to lint.');
        print_help_and_quit();
    }

    for (var i=0; i < config.files.length; i++) {
        var filename = config.files[i];
        var input = readFile(filename);
        if (!input) {
            print("jslint: Couldn't open file '" + filename + "'.");
            quit(1);
        }
        var is_clean = JSLINT(input, config.options);
        if (!is_clean) {
            print("jslint: Lint found in '" + filename + "':");
            print_implied_names();
            print_lint_errors();
        } else {
            print("jslint: No problem found in '" + filename + "'.\n");
        }
    }
}

main([].slice.apply(arguments));
