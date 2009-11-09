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
        "status_value": "Experimental",
        "branch_path": "/~name12/gnome-terminal/klingon",
        "user_can_edit_status": true,
        "status_widget_items": [{
            "style": "",
            "name": "Experimental",
            "css_class": "branchstatusEXPERIMENTAL",
            "value": "Experimental",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Development",
            "css_class": "branchstatusDEVELOPMENT",
            "value": "Development",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Mature",
            "css_class": "branchstatusMATURE",
            "value": "Mature",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Merged",
            "css_class": "branchstatusMERGED",
            "value": "Merged",
            "disabled": false,
            "help": ""},
        {
            "style": "",
            "name": "Abandoned",
            "css_class": "branchstatusABANDONED",
            "value": "Abandoned",
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
        status_choice_edit.plug({
            fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                patch: 'lifecycle_status',
                resource: conf.branch_path}});
        status_choice_edit.render();
    }
};

}, '0.1', {requires: ['node', 'lazr.choiceedit', 'lp.client.plugins']});
