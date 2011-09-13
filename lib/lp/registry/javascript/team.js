/** Copyright (c) 2009-2010, Canonical Ltd. All rights reserved.
 *
 * Team add member animations and ui.
 *
 * @module lp.registry.team
 */

YUI.add('lp.registry.team', function(Y) {

var module = Y.namespace('lp.registry.team');

/*
 * Initialize click handler for the add member link
 *
 * @method setup_add_member_handler
 */
module.setup_add_member_handler = function(step_title) {
    if (Y.UA.ie) {
        return;
    }

    var config = {
        header: 'Add a member',
        step_title: step_title,
        picker_activator: '.menu-link-add_member'
    };

    config.save = _add_member;
    Y.lp.app.picker.create('ValidTeamMember', config);
};

var _add_member = function(selected_person) {
    var box = Y.one('#membership');
    var spinner = box.one('#add-member-spinner');
    var addmember_link = box.one('.menu-link-add_member');
    addmember_link.addClass('unseen');
    spinner.removeClass('unseen');
    var disable_spinner = function() {
        addmember_link.removeClass('unseen');
        spinner.addClass('unseen');
    };
    lp_client = new Y.lp.client.Launchpad();

    var error_handler = new Y.lp.client.ErrorHandler();
    error_handler.clearProgressUI = disable_spinner;
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(addmember_link, error_msg);
    };

    addmember_config = {
        on: {
            success: function(change_and_status) {
                var did_status_change = change_and_status[0];
                var current_status = change_and_status[1];
                var members_section, members_ul, count_elem;
                if (did_status_change === false) {
                    disable_spinner();
                    Y.lp.app.errors.display_info(
                        selected_person.title + ' is already ' +
                        current_status.toLowerCase() +
                        ' as a member of the team.');
                    return;
                }

                if (current_status == 'Invited') {
                    members_section = box.one('#recently-invited');
                    members_ul = box.one('#recently-invited-ul');
                    count_elem = box.one('#invited-member-count');
                } else if (current_status == 'Proposed') {
                    members_section = box.one('#recently-proposed');
                    members_ul = box.one('#recently-proposed-ul');
                    count_elem = box.one('#proposed-member-count');
                } else if (current_status == 'Approved') {
                    members_section = box.one('#recently-approved');
                    members_ul = box.one('#recently-approved-ul');
                    count_elem = box.one('#approved-member-count');
                } else {
                    Y.lp.app.errors.display_error(
                        addmember_link,
                        'Unexpected status: ' + current_status);
                    return;
                }
                var first_node = members_ul.get('firstChild');

                var xhtml_person_handler = function(person_html) {
                    if (count_elem === null && current_status == 'Invited') {
                        count_elem = Y.Node.create(
                            '<strong id="invited-member-count">' +
                            '1</strong>');
                        var count_box = Y.one(
                            '#membership #membership-counts');
                        count_box.append(Y.Node.create(
                            '<span>, </span>'));
                        count_box.append(count_elem);
                        count_box.append(Y.Node.create(
                            '<span> <a href="+members#invited">' +
                            'invited members</a></span>'));
                    } else {
                        var count = count_elem.get('innerHTML');
                        count = parseInt(count, 10) + 1;
                        count_elem.set('innerHTML', count);
                    }
                    person_repr = Y.Node.create(
                        '<li>' + person_html + '</li>');
                    members_section.removeClass('unseen');
                    members_ul.insertBefore(person_repr, first_node);
                    anim = Y.lp.anim.green_flash({node: person_repr});
                    anim.run();
                    disable_spinner();
                };

                xhtml_person_config = {
                    on: {
                        success: xhtml_person_handler,
                        failure: error_handler.getFailureHandler()
                    },
                    accept: Y.lp.client.XHTML
                };
                lp_client.get(selected_person.api_uri, xhtml_person_config);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            // XXX: EdwinGrubbs 2009-12-16 bug=497602
            // Why do I always have to get absolute URIs out of the URIs
            // in the picker's result/client.links?
            reviewer: Y.lp.client.get_absolute_uri(LP.links.me),
            person: Y.lp.client.get_absolute_uri(selected_person.api_uri)
        }
    };

    lp_client.named_post(
        LP.cache.context.self_link, 'addMember', addmember_config);
};

}, '0.1', {requires: ['node',
                      'lp.anim',
                      'lp.app.errors',
                      'lp.app.picker',
                      'lp.client',
                      'lp.client.plugins'
                      ]});
