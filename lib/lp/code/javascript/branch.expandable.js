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
    // Get the URL of the form
    //   https://code.launchpad.dev/+loggerhead/branch/diff/revno
    var branch_name = LP.cache.context.unique_name;
    var branch_url = LP.cache.context.web_link;

    // To construct the URL, we take the branch web link, and insert
    // +loggerhead/ before the branch name, and /diff/revno
    // at the end of the URL.
    return branch_url.replace(branch_name, '+loggerhead/' + branch_name) +
        '/diff/' + rev_number;
}

function bmpGetDiffUrl(start_revno, end_revno) {
    var branch_url = LP.cache.context.web_link;

    var diff_url = LP.cache.branch_diff_link + end_revno;
    if (start_revno !== 0) {
       diff_url += '/' + start_revno;
    }
    return diff_url;
}

function bmp_diff_loader(icon_node, content_node, output_handler) {
    var rev_no_range = icon_node.get('id').replace('expandable-', '').split('-');
    var start_revno = rev_no_range[0]-1;
    var end_revno = rev_no_range[1];

    function nodify_result(diff) {
        var node = Y.Node.create('<table class="diff"></table>');
        var difflines = diff.split('\n');

        for (var i=0; i < difflines.length; i++) {
            var line = Y.Node.create('<td/>');
            line.set('text', difflines[i] + '\n');
            switch (difflines[i][0]) {
                case '+':
                    line.addClass('diff-added');
                    break;
                case '-':
                    line.addClass('diff-removed');
                    break;
            }
            line.addClass('text');
            var row = Y.Node.create('<tr></tr>');
            row.appendChild(line);
            node.appendChild(row);
        }
        output_handler(node);
    }

    var config = {
        on: {
            success: nodify_result,
            failure: function(trid, response, args) {
                output_handler(Y.Node.create('<pre><i>Error</i></pre>'));
            }
        }
    };

    lp_client = new Y.lp.client.Launchpad();
    lp_client.get(bmpGetDiffUrl(start_revno, end_revno), config);
}

function diff_loader(icon_node, content_node, output_handler) {
    var rev_no = icon_node.get('id').replace('expandable-', '');

    function nodify_result(html) {
        var node = Y.Node.create('<pre/>');
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
namespace.bmp_diff_loader = bmp_diff_loader;

}, "0.1", {"requires": ["node", "lp.app.widgets.expander"]});
