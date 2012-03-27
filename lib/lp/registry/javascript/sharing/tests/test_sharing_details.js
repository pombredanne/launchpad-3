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

        test_render_branches: function () {
            var config = {
                branches: [
                    {
                        branch_link:'/~someone/+junk/somebranch',
                        branch_id: '2',
                        branch_name:'lp:~someone/+junk/somebranch'
                    }
                ]
            };
            details_module = Y.lp.registry.sharing.details;
            table_constructor = details_module.SharingDetailsTable;
            var details_widget = new table_constructor(config);
            details_widget.render();
            var expected = "lp:~someone/+junk/somebranch"
            var branch_link = Y.one('#sharing-table-body').one('a');
            var actual_text = branch_link.get('text').replace(/\s+/g, '');
            Assert.areEqual(expected, actual_text);
        },

        test_render_bugs: function () {
            var config = {
                bugs: [
                    {
                        bug_link:'/bugs/2',
                        bug_id: '2',
                        bug_importance: 'critical',
                        bug_summary:'Everything is broken.'
                    }
                ]
            };
            table_constructor = Y.lp.registry.sharing.details.SharingDetailsTable;
            var details_widget = new table_constructor(config);
            details_widget.render();
            var expected = "Everythingisbroken.";
            var bug_link = Y.one('#sharing-table-body').one('a');
            var actual_text = bug_link.get('text').replace(/\s+/g, '');
            Assert.areEqual(expected, actual_text);
        }
    }));


}, '0.1', { 'requires': [ 'test', 'console', 'event',
                          'lp.registry.sharing.details']});
