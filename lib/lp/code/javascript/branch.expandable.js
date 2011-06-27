/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for handling the update of the branch status.
 *
 * @module lp.code.branchstatus
 * @requires node, lazr.choiceedit, lp.client.plugins
 */

YUI.add('lp.code.branch.expandable', function(Y) {

var namespace = Y.namespace('lp.code.branch.expandable');

function getDiffUrl(rev_number) {
    // Sample portlet to load.  Not a real diff!
    return LP.cache.context.web_link + '/+portlet-details';
}

function diff_loader(node) {
    var rev_no = node.get('id').replace('expandable-', '');

    var config = {
        on: {
            success: function(html) {
                var content = Y.lp.app.widgets.expander.getContentNode(node);
                content.set('innerHTML',
                            '<h1>REV ' + rev_no + '</h1>' + html);
            },
            failure: function(trId, response, args) {

            }
        }
    };

    lp_client = new Y.lp.client.Launchpad();
    lp_client.get(getDiffUrl(rev_no), config);

}
namespace.diff_loader = diff_loader;

}, "0.1", {"requires": ["node", "lp.app.widgets.expander"]});
