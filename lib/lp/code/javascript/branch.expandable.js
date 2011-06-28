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
    // Get the URL of the form
    //   https://code.launchpad.dev/+loggerhead/branch/diff/revno/revno-1
    var branch_name = LP.cache.context.unique_name;
    var branch_url = LP.cache.context.web_link;

    // To construct the URL, we take the branch web link, and insert
    // +loggerhead/ before the branch name, and /diff/revno/revno-1
    // at the end of the URL.
    return branch_url.replace(branch_name, '+loggerhead/' + branch_name) +
        '/diff/' + rev_number + '/' + (rev_number - 1);
}

function diff_loader(node) {
    var rev_no = node.get('id').replace('expandable-', '');

    var config = {
        on: {
            success: function(html) {
                var content = Y.lp.app.widgets.expander.getContentNode(node);
                content.set('innerHTML',
                            '<pre>' + html + '</pre>');
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
