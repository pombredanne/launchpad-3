/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

var YUI_config = {
    filter: 'raw',
    combine: false,
    fetchCSS: false
};

YUI.add("lp.testing.runner", function(Y) {

/**
 * Testing utilities.
 *
 * @module lp.testing
 * @namespace lp
 */

var Runner = Y.namespace("lp.testing.Runner");

Runner.run = function(suite) {

    // Lock, stock, and two smoking barrels.
    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    Y.on("domready", function() {
        var yconsole = new Y.Console({
            newestOnTop: false,
            useBrowserConsole: true
        });
        yconsole.render("#log");
        Y.Test.Runner.run();
    });
};

}, "0.1", {"requires": ["oop", "test", "console"]});
