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
    };

    suite.add(new Y.Test.Case({
        name: 'Test branch diff functions',

        /*
         * Diff overlays should reopen with multiple clicks. The widget's
         * visible attribute must be toggled, too.
         */
        test_diff_overlay_multiple_opens: function() {
            // Setup mock client and initialize the link click handler.
            var mock_client = new MockClient();
            var link_node = Y.one('#test-diff-popup');
            var api_url = link_node.one('a.api-ref').getAttribute('href');
            module.link_popup_diff_onclick(link_node, mock_client);

            // Open the overlay once.
            link_node.one('a.diff-link').simulate('click');
            var widget = module.rendered_overlays[api_url];
            var overlay = widget.get('boundingBox');
            Y.Assert.isNotNull(overlay);
            Y.Assert.areEqual(overlay.getStyle('display'), 'block');
            Y.Assert.isTrue(widget.get('visible'));

            // verify that the widget has a header div
            Y.Assert.isNotNull(Y.one('.yui3-widget-hd'));

            // Close the overlay.
            overlay.one('.close a').simulate('click');
            Y.Assert.areEqual(overlay.getStyle('display'), 'none');
            Y.Assert.isFalse(widget.get('visible'));

            // Open it again.
            link_node.one('a.diff-link').simulate('click');
            Y.Assert.areEqual(overlay.getStyle('display'), 'block');
            Y.Assert.isTrue(widget.get('visible'));
        }

        }));

    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    // keep the default console object so we can debug with our dev tools while
    // still allow us to log to the YUI Console via Y.log and yconsole
    var yconsole = new Y.Console({newestOnTop: false});
    yconsole.render('#log');

    // Start the test runner on Y.after to ensure all setup has had a
    // chance to complete.
    Y.after('domready', function() {
        Y.Test.Runner.run();
    });
});
