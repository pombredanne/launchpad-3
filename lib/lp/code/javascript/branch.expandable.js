/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling the update of the branch status.
 *
 * @module lp.code.branchstatus
 * @requires node, lp.client.plugins
 */

YUI.add('lp.code.branch.expandable', function(Y) {

var namespace = Y.namespace('lp.code.branch.expandable');

function getDiffUrl(rev_number) {
    // Sample portlet to load.  Not a real diff!
    return LP.cache.context.web_link + '/+portlet-details';
}

function diff_loader(node, output_handler) {
    var rev_no = node.get('id').replace('expandable-', '');

    function nodify_result(html) {
        var node = Y.Node.create('<div/>');
        node.set('innerHTML', html);
        output_handler(node);
    }

    var config = {
        on: {
            success: nodify_result,
            failure: function(trid, response, args) {
                nodify_result("<i>Error</i>");
            }
        }
    };

    lp_client = new Y.lp.client.Launchpad();
    lp_client.get(getDiffUrl(rev_no), config);
}

namespace.diff_loader = diff_loader;

}, "0.1", {"requires": ["node", "lp.app.widgets.expander"]});
