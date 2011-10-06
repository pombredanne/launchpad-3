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
var mynamespace = Y.lp.mynamespace;
var suite = new Y.Test.Suite("mynamespace Tests");

suite.add(new Y.Test.Case({
    // Test the setup method.
    name: 'setup',

    _should: {
        error: {
            test_config_undefined: true
            // Careful: no comma after last item or IE chokes.
            }
        },

    setUp: function() {
        this.tbody = Y.get('#milestone-rows');
        },

    tearDown: function() {
        delete this.tbody;
        mynamespace._milestone_row_uri_template = null;
        mynamespace._tbody = null;
        },

    test_good_config: function() {
        // Verify the config data is stored.
        var config = {
            milestone_row_uri_template: '/uri',
            milestone_rows_id:  '#milestone-rows'
            };
        mynamespace.setup(config);
        Y.Assert.areSame(
            config.milestone_row_uri_template,
            mynamespace._milestone_row_uri_template);
        Y.Assert.areSame(this.tbody, mynamespace._tbody);
        },

    test_config_undefined: function() {
        // Verify an error is thrown if there is no config.
        mynamespace.setup();
        }
        // Careful: no comma after last item or IE chokes.
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
