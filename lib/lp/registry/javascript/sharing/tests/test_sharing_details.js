/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */
YUI.add('lp.registry.sharing.details.test', function(Y) {

// Local aliases
    var Assert = Y.Assert,
        ArrayAssert = Y.ArrayAssert;
    var sharing_details = Y.lp.registry.sharing.details;

    var tests = Y.namespace('lp.registry.sharing.details.test');
    tests.suite = new Y.Test.Suite(
        "lp.registry.sharing.details Tests");

    tests.suite.add(new Y.Test.Case({
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
            var expected = "lp:~someone/+junk/somebranch"
            var branch_link = Y.one('#sharing-table-body').one('a');
            var actual_text = branch_link.get('text').replace(/\s+/g, '');
            Assert.areEqual(expected, actual_text);
        }

    }));


}, '0.1', { 'requires': [ 'test', 'console', 'event',
                          'lp.registry.sharing.details']});
