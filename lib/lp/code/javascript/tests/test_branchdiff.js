/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for lp.code.branchmergeproposal.diff.
 *
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false
    }).use('test', 'console', 'node-event-simulate', 'lp.client',
           'lp.code.branchmergeproposal.diff', function(Y) {

    var module = Y.lp.code.branchmergeproposal.diff;
    var suite = new Y.Test.Suite("branchmergeproposal.diff Tests");

    suite.add(new Y.Test.Case({
        name: 'Test branch diff functions',

        test_diff_overlay_multiple_opens: function() {
            var link_node = Y.one('#test-diff-popup');
            module.link_popup_diff_onclick(link_node);
            link_node.one('a.diff-link').simulate('click');
            var overlay = Y.one('#yui3-pretty-overlay-modal');
            Y.Assert.isNotNull(overlay);
        }

        }));

    var handle_complete = function(data) {
        status_node = Y.Node.create(
            '<p id="complete">Test status: complete</p>');
        Y.one('body').appendChild(status_node);
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
