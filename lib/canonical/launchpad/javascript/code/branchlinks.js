/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Code for handling links to branches from bugs and specs.
 *
 * @module BranchLinks
 * @requires base, node, lazr.anim, lazr.formoverlay
 */

YUI.add('code.branchlinks', function(Y) {

Y.code = Y.namespace('code');
Y.code.branchlinks = Y.namespace('code.branchlinks');

var lp_client;
var lp_branch_entry;

var link_bug_overlay;

function show_link_to_bug_overlay(e) {

    link_bug_overlay = Y.lazr.FormOverlay({
        headerContent: '<h2>Link to a bug</h2>',
        form_content: 'foo',
        form_submit_button: Y.Node.create(
            '<button type="submit" name="field.actions.change" ' +
            'value="Change" class="lazr-pos lazr-btn">Ok</button>'),
        form_cancel_button: Y.Node.create(
            '<button type="button" name="field.actions.cancel" ' +
            'class="lazr-neg lazr-btn">Cancel</button>'),
        centered: true,
        form_submit_callback: subscribe_yourself_inline,
        visible: true
    });
}

/*
 * Get the bugnumber for the element id
 */
function get_bugnumber_from_id(id) {
}

/*
 * Get the bug representation from the bugnumber.
 */
function get_bug_from_bugnumber(number) {
    if (lp_client == undefined) {
        lp_client = new LP.client.Launchpad();
    }
    if (lp_branch_entry === undefined) {
        var lp_branch_repr = LP.client.cache.context;
        lp_branch_entry = new LP.client.Entry(
            lp_client, branch_repr, branch_repr.self_link);
    }
}


}, '0.1', {requires: ['base', 'lazr.anim', 'lazr.formoverlay']});
