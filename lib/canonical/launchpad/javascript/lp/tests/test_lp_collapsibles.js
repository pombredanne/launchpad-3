/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../icing/yui/current/build/',
    filter: 'raw',
    combine: false
    }).use('yuitest', 'console', function(Y) {

    var yconsole = new Y.Console({
        newestOnTop: false
    });
    yconsole.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
    });
});
