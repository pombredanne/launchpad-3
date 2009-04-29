/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Bugtask editing.
 *
 * @module BugTaskEdit
 * @requires base, node, substitute
 */

YUI.add('bugs.bugtask_edit', function(Y) {

var bugs = Y.namespace('bugs');

/**
 * Set up the bug tasks table.
 *
 * Called once, as soon as the DOM is ready, to initialize the page.
 *
 * @method setup_bugtasks_table
 */
bugs.setup_bugtask_row = function(row_id, bugtask_url, status_widget_items) {
    var tr = Y.get('#' + row_id);
    var status_content = tr.query('.status-content');
    var edit_icon = tr.query('.editicon');
    var status_choice_edit = new Y.ChoiceSource({
        contentBox: status_content,
        value: status_content.getAttribute('current_value'),
        title: 'Change status to',
        items: status_widget_items
    });
    status_choice_edit.showError = function(err) {
        alert(err);
    };
    status_choice_edit.on('save', function(e) {
        var cb = status_choice_edit.get('contentBox');
        Y.Array.each(status_widget_items, function(item) {
            if (item.value == status_choice_edit.get('value')) {
                cb.addClass(item.css_class);
            } else {
                cb.removeClass(item.css_class);
            }
        });
    });
    status_choice_edit.plug({
        fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                patch: 'status',
                resource: bugtask_url}});
    status_choice_edit.render();
    status_content.on('mouseover', function(e) {
        edit_icon.set('src', '/@@/edit')
    });
    status_content.on('mouseout', function(e) {
        edit_icon.set('src', '/@@/edit-grey')
    });
    status_content.setStyle('cursor', 'pointer');
};
}, '0.1', {requires: ['node', 'substitute', 'base', 'widget-position-ext',
                      'lazr.base', 'lazr.overlay', 'lazr.choiceedit',
                      'lp.client.plugins']});

