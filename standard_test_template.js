/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false

// Don't forget to add the module under test to the use() clause.

      }).use('event', 'lp.client', 'node', 'test', 'widget-stack',
             'console', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;

var suite = new Y.Test.Suite("YOUR TEST SUITE NAME");

suite.add(new Y.Test.Case({

    name: 'A TEST CASE NAME',

    setUp: function() {
        // Monkeypatch LP to avoid network traffic and to make
        // some things work as expected.
        Y.lp.client.Launchpad.prototype.named_post =
          function(url, func, config) {
            config.on.success();
          };
        LP = {
          'cache': {
            'bug': {
              self_link: "http://bugs.example.com/bugs/1234"
          }}};
    },

    tearDown: function() {
    },

    /**
     * The choice edit should be displayed inline.
     */
    test_something: function() {
        // Test something
    },

}));

var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
