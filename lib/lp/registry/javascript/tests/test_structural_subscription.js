/* Copyright (c) 2009-2010, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    // XXX: This gives us pretty CSS; change it to false before landing.
    fetchCSS: true
    }).use('test', 'console', 'lp.registry.structural_subscription', function(Y) {

    var suite = new Y.Test.Suite("Structural subscription overlay tests");

    suite.add(new Y.Test.Case({
        // Test the setup method.
        name: 'Structural Subscription Overlay',

        _should: {
            error: {
                }
        },

        setUp: function() {
        },

        tearDown: function() {
        },

        test_something: function() {
        },

        })
    );

    // Lock, stock, and two smoking barrels.
    var handle_complete = function(data) {
        status_node = Y.Node.create(
            '<p id="complete">Test status: complete</p>');
        Y.one('body').appendChild(status_node);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
