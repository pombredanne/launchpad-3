/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for lp.code.branch.revisionexpander.
 *
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false
    }).use('test', 'console', 'node-event-simulate', 'lp.client',
           'lp.code.branch.revisionexpander', function(Y) {

    var module = Y.lp.code.branch.revisionexpander;
    var suite = new Y.Test.Suite("branch.revisionexpander Tests");

    suite.add(new Y.Test.Case({
        name: 'Test branch diff functions',

        /*
         * Unified diffs are rendered to a table, one row per line
         */
        test_difftext_to_node_outputs_table: function() {
            var samplediff = (
                "=== modified file 'README'\n" +
                "--- README 2011-01-20 23:05:06 +0000\n" +
                "+++ README 2011-06-30 10:47:28 +0000\n" +
                "@@ -1,3 +1,4 @@\n" +
                "+Green sheep!\n" +
                " =========\n" +
                " testtools\n" +
                " =========\n" +
                "            \n");
            var node = module.difftext_to_node(samplediff);
            Y.Assert.areEqual('TABLE', node.get('tagName'));
            Y.Assert.isTrue(node.hasClass('diff'));
            /* samplediff has 9 lines, so the table will have 9 rows
             * (trailing newlines don't result in a final row containing an
             * empty string) */
            Y.Assert.areEqual(9, node.get('children').size());
        },

        /*
         * Diffs are not interpreted as HTML.
         */
        test_difftext_to_node_escaping: function() {
            var node = module.difftext_to_node("<p>hello</p>");
            var td = node.one('td');
            Y.Assert.isNull(td.one('p'));
        }
        }));

    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    // Start the test runner on Y.after to ensure all setup has had a
    // chance to complete.
    Y.after('domready', function() {
        Y.Test.Runner.run();
    });
});

