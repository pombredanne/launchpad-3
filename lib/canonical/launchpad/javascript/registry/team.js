/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Objects for subscription handling.
 *
 * @module lp.subscriber
 */

YUI.add('lp.team', function(Y) {

Y.namespace('lp');

/*
 * Initialize click handler for the add member link
 *
 * @method setup_add_member_handler
 */
function setup_add_member_handler() {
    var config = {
        header: 'Add a member',
        step_title: 'Search'
    };

    var picker = Y.lp.picker.create(
        'ValidTeamMember',
        function(result) { add_member(result); },
        config);
    // Clear results and search terms on cancel or save.
    // XXX: None of the below should be needed -- it could be the default
    // behaviour of the picker itself.
    picker.on('save', clear_picker, picker);
    picker.on('cancel', clear_picker, picker);

    var addmember_link = Y.one('.menu-link-add_member');
    addmember_link.on('click', function(e) {
        e.halt();
        picker.show();
    });
    addmember_link.addClass('js-action');
}


function add_member(result) {

    var spinner = Y.one('#add-member-spinner');
    var addmember_link = Y.one('.menu-link-add_member');
    addmember_link.setStyle('display', 'none');
    spinner.setStyle('display', 'inline');
    function disable_spinner() {
        addmember_link.setStyle('display', 'inline');
        spinner.setStyle('display', 'none');
    }
    lp_client = new LP.client.Launchpad();

    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = disable_spinner;
    error_handler.showError = function(error_msg) {
        Y.lp.display_error(Y.one('.menu-link-add_member'), error_msg);
    };

    config = {
        on: {
            success: function(member_added) {
                if (!member_added) {
                    disable_spinner();
                    alert('Already a member.');
                    return;
                }
                if ( result.css.match("team") ) {
                    disable_spinner();
                    alert('This is a team');
                    return;
                }
                var members_section = Y.one('#recently-approved-ul');
                var first_node = members_section.get('firstChild');
                config = {
                    on: {
                        success: function(person_html) {
                            var total_members = Y.one(
                                '#member-count').get('innerHTML');
                            total_members = parseInt(total_members) + 1;
                            Y.one('#member-count').set(
                                'innerHTML', total_members);
                            person_repr = Y.Node.create(
                                '<li>' + person_html + '</li>');
                            members_section.insertBefore(
                                person_repr, first_node);
                            anim = Y.lazr.anim.green_flash(
                                {node: person_repr});
                            anim.run()
                            disable_spinner();
                        },
                        failure: error_handler.getFailureHandler()
                    },
                    accept: LP.client.XHTML
                };
                lp_client.get(result.api_uri, config);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            // XXX: Why do I always have to get absolute URIs out of the URIs
            // in the picker's result/client.links?
            reviewer: LP.client.get_absolute_uri(LP.client.links.me),
            person: LP.client.get_absolute_uri(result.api_uri)
        }
    };

    lp_client.named_post(
        LP.client.cache.context.self_link, 'addMember', config);
}

/*
 * Clear the add member picker.
 * XXX: shamelessly copied from bugtask-index.js
 *
 * @method clear_picker
 * @param e {Object} The event object.
 */
function clear_picker(e) {
    var input = Y.one('.yui-picker-search-box input');
    input.set('value', '');
    this.set('error', '');
    this.set('results', [{}]);
    this._results_box.set('innerHTML', '');
    this.set('batches', []);
}

Y.lp.setup_add_member_handler = setup_add_member_handler;

}, '0.1', {requires: ['base', 'node']});
