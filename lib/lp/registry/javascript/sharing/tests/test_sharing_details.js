/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */
YUI({
    base: '../../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
}).use('event', 'lp.mustache', 'node', 'node-event-simulate', 'test',
       'widget-stack', 'console', 'lp.registry.sharing.details',
       function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;
var sharing_details = Y.lp.registry.sharing.details;
var suite = new Y.Test.Suite("sharing.details Tests");

suite.add(new Y.Test.Case({

    name: 'Sharing Details',

    setUp: function() {
        window.LP = {
            links: {},
            cache: {}
        };
    },

    tearDown: function() {
    },

    test_render: function () {
        var config = {
            branches: [
                {
                    branch_link:'/~someone/+junk/somebranch',
                    branch_id: '2',
                    branch_name:'lp:~someone/+junk/somebranch'
                }
            ]
        };
        table_constructor = Y.lp.registry.sharing.details.SharingDetailsTable;
        var details_widget = new table_constructor(config);
        details_widget.render();
        var table = Y.one('#sharing-table-body');
        var expected = "lp:~someone/+junk/somebranch--";
        var actual_text = table.get('text').replace(/\s+/g, '');
        Assert.areEqual(expected, actual_text);
    }

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
