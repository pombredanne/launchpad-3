/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling form elements on Code domain pages.
 *
 * @module Y.lp.code.util
 * @requires node
 */
YUI.add('lp.code.util', function(Y) {
var ns = Y.namespace('lp.code.util');

var submit_filter = function (e) {
    Y.one('#filter_form').submit();
};

var hookUpBranchFilterSubmission = function() {
    Y.one("[id='field.lifecycle']").on('change', submit_filter);
    var sortby = Y.one("[id='field.sort_by']");
    if (Y.Lang.isValue(sortby)) {
        sortby.on('change', submit_filter);
    }
    var category = Y.one("[id='field.category']");
    if (Y.Lang.isValue(category)) {
        category.on('change', submit_filter);
    }
    Y.one('#filter_form_submit').addClass('hidden');
};

var hookUpMergeProposalFilterSubmission = function() {
    Y.one("[id='field.status']").on('change', submit_filter);
    Y.one('#filter_form_submit').addClass('hidden');
};

var hookUpRetryImportSubmission = function() {
    var try_again_link = Y.one("#tryagainlink");
    try_again_link.on('click', function (e) {
        Y.one('#tryagain').submit();
    });
    try_again_link.removeClass('hidden');
    Y.one('[id="tryagain.actions.tryagain"]').addClass('hidden');
};

ns.hookUpBranchFilterSubmission = hookUpBranchFilterSubmission;
ns.hookUpMergeProposalFilterSubmission = hookUpMergeProposalFilterSubmission;
ns.hookUpRetryImportSubmission = hookUpRetryImportSubmission;

}, "0.1", {"requires": ["node", "dom"]});
