/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Code for handling the update of the branch status.
 *
 * @module branchstatus
 * @requires node, lazr.choiceedit, lp.client.plugins
 */

YUI.add('code.branchmergeproposal', function(Y) {

Y.code.branchmergeproposal = Y.namespace('code.branchmergeproposal');

/*
 * Connect the branch status to the javascript events.
 */
Y.code.branchmergeproposal.connect_status = function() {

    var status_content = Y.get('#branchmergeproposal-status-value');

    /* status values */
    var conf = {
        "status_value": "Work in progress",
        "branch_path": "/~name12/gnome-terminal/klingon",
        "user_can_edit_status": true,
        "status_widget_items": [{
            "style": "",
            "name": "Work in progress",
            "css_class": "mergestatusWORK_IN_PROGRESS",
            "value": "Work in progress",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Needs review",
            "css_class": "mergestatusNEEDS_REVIEW",
            "value": "Needs review",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Approved",
            "css_class": "mergestatusAPPROVED",
            "value": "Approved",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Merged",
            "css_class": "mergestatusMERGED",
            "value": "Merged",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Rejected",
            "css_class": "mergestatusREJECTED",
            "value": "Rejected",
            "disabled": false,
            "help": ""}]};

    if (conf.user_can_edit_status) {
        var status_choice_edit = new Y.ChoiceSource({
            contentBox: status_content,
            value: conf.status_value,
            title: 'Change status to',
            items: conf.status_widget_items});
        status_choice_edit.showError = function(err) {
            display_error(null, err);
        };
        status_choice_edit.on('save', function(e) {
            var cb = status_choice_edit.get('contentBox');
            Y.Array.each(conf.status_widget_items, function(item) {
                if (item.value == status_choice_edit.get('value')) {
                    cb.query('span').addClass(item.css_class);
                } else {
                    cb.query('span').removeClass(item.css_class);
                }
            });
        });
        /*status_choice_edit.plug({
            fn: Y.lp.client.plugins.PATCHPlugin,
            cfg: {
                patch: 'lifecycle_status',
                resource: conf.branch_path}});*/
        status_choice_edit.render();
    }
};

}, '0.1', {requires: ['node', 'lazr.choiceedit', 'lp.client.plugins']});
