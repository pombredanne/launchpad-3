/** Copyright (c) 2012, Canonical Ltd. All rights reserved.
 *
 * Code for handling the update of the branch merge proposals.
 *
 * @module lp.code.branchmergeproposal.nominate
 */

YUI.add('lp.code.branchmergeproposal.nominate', function(Y) {

var namespace = Y.namespace('lp.code.branchmergeproposal.nominate');

var lp_client;

/**
 * Picker validation callback which confirms that the nominated reviewer can
 * be given visibility to the specified branches.
 * @param branches_to_check
 * @param branch_info
 * @param picker
 * @param save_fn
 * @param cancel_fn
 */
var confirm_reviewer = function(branches_to_check, branch_info, picker,
                                save_fn, cancel_fn) {
    var visible_branches = branch_info.visible_branches;
    if (Y.Lang.isArray(visible_branches)
            && visible_branches.length !== branches_to_check.length) {
        var invisible_branches = branches_to_check.filter(function(i) {
            return visible_branches.indexOf(i) < 0;
        });
        var yn_content = Y.lp.mustache.to_html([
        "<p class='large-warning' style='padding:12px 2px 0 36px;'>",
        "{{person_name}} does not currently have permission to ",
        "view branches:",
        "<ul style='margin-left: 50px'>",
        "    {{#invisible_branches}}",
        "        <li>{{.}}</li>",
        "    {{/invisible_branches}}",
        "</ul>",
        "</p>",
        "<p>If you proceed, {{person_name}} will be subscribed to the " +
        "branches.</p>",
        "<p>Do you really want to nominate them as a reviewer?</p>"
        ].join(''), {
            invisible_branches: invisible_branches,
            person_name: branch_info.person_name
        });
        Y.lp.app.picker.yesno_save_confirmation(
                picker, yn_content, "Nominate", "Choose Again",
                save_fn, cancel_fn);
    } else {
        if (Y.Lang.isFunction(save_fn)) {
            save_fn();
        }
    }
};

var check_reviewer_can_see_branches = function(picker, value, save_fn,
                                               cancel_fn) {
    if (value === null || !Y.Lang.isValue(value.api_uri)) {
        if (Y.Lang.isFunction(save_fn)) {
            save_fn();
            return;
        }
    }

    var reviewer_uri = Y.lp.client.normalize_uri(value.api_uri);
    reviewer_uri = Y.lp.client.get_absolute_uri(reviewer_uri);
    var error_handler = new Y.lp.client.ErrorHandler();
    error_handler.showError = function(error_msg) {
        picker.set('error', error_msg);
    };

    var branches_to_check = [LP.cache.context.unique_name];
    var target_name = Y.DOM.byId('field.target_branch.target_branch').value;
    if (Y.Lang.trim(target_name) !== '') {
        branches_to_check.push(target_name);
    }
    var confirm = function(branch_info) {
        namespace.confirm_reviewer(
            branches_to_check, branch_info, picker, save_fn, cancel_fn);
    };
    var y_config =  {
        on: {
            success: confirm,
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            person: reviewer_uri,
            branch_names: branches_to_check
        }
    };
    lp_client.named_get("/branches", "getBranchVisibilityInfo", y_config);
};

var setup_reviewer_confirmation = function() {
    var validation_namespace = Y.namespace('lp.app.picker.validation');
    var widget_id = 'show-widget-field-reviewer';
    validation_namespace[widget_id]= check_reviewer_can_see_branches;
};

// XXX wallyworld 2012-02-03 bug=925818
// We should construct YUI objects and widgets as required and not just
// attach stuff to the namespace.
// For testing
namespace.setup_reviewer_confirmation = setup_reviewer_confirmation;
namespace.check_reviewer_can_see_branches = check_reviewer_can_see_branches;
namespace.confirm_reviewer = confirm_reviewer;

// We want to disable the review_type field if no reviewer is
// specified. In such cases, the reviewer will be set by the back end
// to be the default for the target branch and the review type will be None.
var reviewer_changed = function(value) {
    var reviewer = Y.Lang.trim(value);
    var review_type = Y.DOM.byId('field.review_type');
    review_type.disabled = (reviewer === '');
};

namespace.setup = function(conf) {
    lp_client = new Y.lp.client.Launchpad(conf);
    Y.on('blur',
      function(e) {
        reviewer_changed(e.target.get('value'));
      },
      Y.DOM.byId('field.reviewer'));
    var f = Y.DOM.byId('field.reviewer');
    reviewer_changed(f.value);

    setup_reviewer_confirmation();
};

}, "0.1", {"requires": ["io", "substitute", "dom", "node",
   "event", "lp.client", "lp.mustache", "lp.app.picker"]});
