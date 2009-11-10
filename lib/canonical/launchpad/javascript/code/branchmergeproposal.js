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
Y.code.branchmergeproposal.connect_status = function(conf) {

    var status_content = Y.get('#branchmergeproposal-status-value');

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
            config = {
                on: {
                    success: function(entry) {
                        var cb = status_choice_edit.get('contentBox');
                        Y.Array.each(conf.status_widget_items, function(item) {
                            if (item.value == status_choice_edit.get(
                                                                    'value')) {
                                cb.query('span').addClass(item.css_class);
                            } else {
                                cb.query('span').removeClass(item.css_class);
                            }
                        });
                    },
                    //failure: error_handler.getFailureHandler()
                },
                parameters: {
                    status: status_choice_edit.get('value'),
                }
            };
            lp_client = new LP.client.Launchpad();
            lp_client.named_post(
                LP.client.cache.context.self_link, 'setStatus', config);

        });
        status_choice_edit.render();
    }
};

}, '0.1', {requires: ['io', 'node', 'lazr.choiceedit', 'lp.client.plugins']});
