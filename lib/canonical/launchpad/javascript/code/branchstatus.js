/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Code for handling links to branches from bugs and specs.
 *
 * @module branchstatus
 * @requires base, lazr.anim, lazr.formoverlay
 */

YUI.add('code.branchstatus', function(Y) {

Y.branchstatus = Y.namespace('code.branchstatus');

var lp_client;          // The LP client

var link_bug_overlay;

var error_handler;

/*
 * Connect the links to the javascript events.
 */
Y.branchstatus.connect_status = function(conf) {

    var status_content = Y.get('#branch-details-status-value');

    if (conf.user_can_edit_status) {
        var status_choice_edit = new Y.ChoiceSource({
            contentBox: status_content,
            value: conf.status_value,
            title: 'Change status to',
            items: conf.status_widget_items,
            elementToFlash: status_content,
            backgroundColor: '#FFFFFF'
            });
        status_choice_edit.showError = function(err) {
            display_error(null, err);
        };
        importance_choice_edit.on('save', function(e) {
            var cb = importance_choice_edit.get('contentBox');
            Y.Array.each(conf.status_widget_items, function(item) {
                if (item.value == status_choice_edit.get('value')) {
                    cb.addClass(item.css_class);
                } else {
                    cb.removeClass(item.css_class);
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

}