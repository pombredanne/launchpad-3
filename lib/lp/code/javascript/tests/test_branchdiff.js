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

    /*
     * A Mock client that always calls success on get.
     */
    var MockClient = function() {};
    MockClient.prototype = {
        'get': function(uri, config) {
            var content = Y.Node.create('<p>Sample diff.</p>');
            config.on.success(content);
        }
    }

    suite.add(new Y.Test.Case({
        name: 'Test branch diff functions',

        /*
         * Diff overlays should reopen with multiple clicks.
         */
        test_diff_overlay_multiple_opens: function() {
            // Setup mock client and initialize the link click handler.
            var mock_client = new MockClient();
            var link_node = Y.one('#test-diff-popup');
            module.link_popup_diff_onclick(link_node, mock_client);
            // Open the overlay once.
            link_node.one('a.diff-link').simulate('click');
            var overlay = Y.one('.yui3-pretty-overlay');
            Y.Assert.isNotNull(overlay);
            Y.Assert.areEqual(overlay.getStyle('display'), 'block');
            // Close the overlay.
            overlay.one('.close a').simulate('click');
            Y.Assert.areEqual(overlay.getStyle('display'), 'none');
            // Open it again.
            link_node.one('a.diff-link').simulate('click');
            Y.Assert.areEqual(overlay.getStyle('display'), 'block');
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
