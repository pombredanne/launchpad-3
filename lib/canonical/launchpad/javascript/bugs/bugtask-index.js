/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module BugtaskIndex
 * @requires base, node, lazr.formoverlay, lazr.anim
 */

YUI.add('bugs.bugtask_index', function(Y) {

var bugs = Y.namespace('bugs');

/*
 * The lazr.FormOverlay object.
 */
var duplicate_form_overlay;
var privacy_form_overlay;

/*
 * The url of the page used to update bug duplicates.
 */
var update_dupe_url;

/*
 * The launchpad js client that will be used to update the duplicate.
 */
var lp_client;

/*
 * The initially hidden subscribtion spinner element.
 */
var spinner;

/*
 * The launchpad client entry for the current bug.
 */
var lp_bug_entry;
var bug_repr;
var me;
var short_name;
var display_name;
var error_overlay;
var form_load_callbacks = {};
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';
var privacy_link;


Y.bugs.setup_bugtask_index = function() {
    /*
     * Check the page for links related to overlay forms and request the HTML
     * for these forms.
     */
    Y.on('load', function() {
        // If the user is not logged in, then we need to defer to the
        // default behaviour.
        if (LP.client.links.me === undefined){
            return;
        }

        me = LP.client.links['me'];
        short_name = me.substring(2);

        // Create the lp client and bug entry if we haven't done so already.
        if (lp_client === undefined) {
            lp_client = new LP.client.Launchpad();
        }

        if (bug_repr === undefined) {
            bug_repr = LP.client.cache.bug;
            lp_bug_entry = new LP.client.Entry(
                lp_client, bug_repr, bug_repr.self_link);
        }

        config = {
            on: {
                success: function(person) {
                    display_name = person.lookup_value('display_name');
                },
                failure: function(args) {
                    display_error(null, 'Could not find your account.');
                }
            }
        }
        lp_client.get(me, config);

        Y.on('io:complete', function(id, response_object) {
            form_load_callbacks[id](response_object.responseText);
        }, this);

        // First look for 'Mark as duplicate' links.
        var update_dupe_links = Y.all('.menu-link-mark-dupe');

        // If there are none, check for any 'change duplicate bug' links.
        if (!update_dupe_links){
            update_dupe_links = Y.all('#change_duplicate_bug');
        }

        if (update_dupe_links) {
            // First things first, pre-load the mark-dupe form.
            update_dupe_url = update_dupe_links.item(0).getAttribute('href');
            var mark_dupe_form_url = update_dupe_url + '/++form++';
            var dupe_form_id = Y.io(mark_dupe_form_url);
            form_load_callbacks[dupe_form_id.id] = createBugDuplicateFormOverlay;

            // Add an on-click handler to any links found that displays
            // the form overlay.
            update_dupe_links.on('click', function(e){
                // Only go ahead if we have received the form content by the
                // time the user clicks:
                if (duplicate_form_overlay){
                    e.preventDefault();
                    duplicate_form_overlay.show();
                }
            });
            // Add a class denoting them as js-action links.
            update_dupe_links.addClass('js-action');
        }

        privacy_link = Y.get('#privacy-link');

        if (privacy_link) {
            var privacy_link_url = privacy_link.getAttribute('href') + '/++form++';
            var privacy_div = Y.get('#privacy-text');
            var privacy_text = privacy_link.get('innerHTML') + ' ';
            privacy_div.set('innerHTML', privacy_text);
            privacy_link = Y.Node.create(
                '<a href="' + privacy_link_url + '" id="privacy-link">' +
                '<img src="/@@/edit"></a>');
            privacy_div.appendChild(privacy_link);
            var privacy_form_id = Y.io(privacy_link_url);
            form_load_callbacks[privacy_form_id.id] = create_privacy_form_overlay;

            privacy_link.on('click', function(e) {
                if (privacy_form_overlay) {
                    e.preventDefault();
                    privacy_form_overlay.show();
                    // XXX Abel Deuring 2009-04-23, bug 365462
                    // Y.get('#field.private') returns null.
                    // Seems that YUI does not like IDs containing a '.'
                    document.getElementById('field.private').focus();
                }
            });
            privacy_link.addClass('js-action');
        }

        spinner = Y.get('#sub-unsub-spinner');

        subscription_link = Y.get('.menu-link-subscription');
        subscription_link.on('click', function(e) {
            e.halt();
            if (e.target.get('innerHTML') == 'Subscribe') {
                subscribe_current_user(e.target);
            }
            else {
                unsubscribe_current_user(e.target);
            }
        });
        subscription_link.addClass('js-action');


        // The unsubscribe icon in the scribers list has to be
        // handled uniquely.
        var unsubscribe_icon = Y.get('#unsubscribe-icon-' + me.substring(2));
        if (unsubscribe_icon) {
            unsubscribe_icon.on('click', function(e) {
                e.halt();
                unsubscribe_user_via_icon(e.target, subscription_link);
            });
        }

        create_error_overlay();
    }, window);
}

/*
 * Creates the duplicate form overlay using the passed form content.
 */
function createBugDuplicateFormOverlay(form_content) {
    duplicate_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Mark bug report as duplicate</h2>',
        form_content: 'Marking the bug as a duplicate will, by default, ' +
                      'hide it from search results listings.' + form_content,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        form_submit_callback: update_bug_duplicate,
        visible: false
    });
    duplicate_form_overlay.render('#duplicate-form-container');
}

/*
 * Update the bug duplicate via the LP API
 */
function update_bug_duplicate(data) {
    // Hide the formoverlay:
    duplicate_form_overlay.hide();

    // Add the spinner...
    var dupe_span = Y.get('#mark-duplicate-text');
    dupe_span.addClass('update-in-progress-message');

    // Set the new duplicate link on the bug entry.
    var new_dup_url = null;
    var new_dup_id = data['field.duplicateof'];
    // "make lint" claims the expession operator below should be "!--".
    // If we use this operator, we cannot unset the duplicate number.
    if (new_dup_id != '') {
        var self_link = lp_bug_entry.get('self_link');
        var last_slash_index = self_link.lastIndexOf('/');
        new_dup_url = self_link.slice(0, last_slash_index+1) + new_dup_id;
    }
    var old_dup_url = lp_bug_entry.get('duplicate_of_link');
    lp_bug_entry.set('duplicate_of_link', new_dup_url);

    // Create a config for the lp_save method
    config = {
        on: {
            success: function(updated_entry) {
                dupe_span.removeClass('update-in-progress-message');
                lp_bug_entry = updated_entry;

                // XXX noodles 2009-03-17 bug=336866 It seems the etag
                // returned by lp_save() is incorrect. Remove it for now
                // so that the second save does not result in a '412
                // precondition failed' error.
                lp_bug_entry.removeAtt('http_etag');

                if (new_dup_url !== null) {
                    dupe_span.set('innerHTML', [
                        'Duplicate of <a href="/bugs/' + new_dup_id + '">',
                        'bug #' + new_dup_id +'</a> ',
                        '<a class="menu-link-mark-dupe js-action" ',
                        'href="' + update_dupe_url + '">',
                        '<img src="/@@/edit" /></a>'
                        ].join(''));
                } else {
                    dupe_span.set('innerHTML',
                        '<a class="menu-link-mark-dupe js-action" href="' +
                        update_dupe_url + '">' +
                        '<img src="/@@/bug-dupe-icon" /> ' +
                        'Mark as duplicate</a>');
                }
                Y.lazr.anim.green_flash({node: dupe_span}).run();
                // ensure the new link is hooked up correctly:
                dupe_span.query('a.menu-link-mark-dupe').on(
                    'click', function(e){
                        e.preventDefault();
                        duplicate_form_overlay.show();
                    });
            },
            failure: function(id, request) {
                dupe_span.removeClass('update-in-progress-message');
                if (request.status == 400) {
                    duplicate_form_overlay.showError(
                        new_dup_id + ' is not a valid bug number or' +
                        ' nickname.');
                } else {
                    duplicate_form_overlay.showError(request.responseText);
                }
                duplicate_form_overlay.show();

                // Reset the lp_bug_entry.duplicate_of_link as it wasn't
                // updated.
                lp_bug_entry.set('duplicate_of_link', old_dup_url);

            }
        }
    };

    // And save the updated entry.
    lp_bug_entry.lp_save(config);
}

/*
 * Create the privacy settings form overlay.
 *
 * @method create_privacy_form_overlay
 * @param form_content {string} The HTML data of the form overlay.
 */
var create_privacy_form_overlay = function(form_content) {
    privacy_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Change privacy settings</h2>',
        form_content: form_content,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        form_submit_callback: update_privacy_settings,
        visible: false
    });
    privacy_form_overlay.render('#privacy-form-container');
    var node = Y.get('#form-container');
};

var update_privacy_settings = function(data) {
    privacy_form_overlay.hide();

    var privacy_text = Y.get('#privacy-text');
    privacy_text.addClass('update-in-progress-message');

    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }

    if (lp_bug_entry === undefined) {
        var bug_repr = LP.client.cache.bug;
        lp_bug_entry = new LP.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);
    }

    var private = data['field.private'] !== undefined;
    var security_related =
        data['field.security_related'] !== undefined;

    lp_bug_entry.set('private', private);
    lp_bug_entry.set('security_related', security_related);

    var config = {
        on: {
            success: function (updated_entry) {
                var privacy_text = Y.get('#privacy-text');
                privacy_text.removeClass('update-in-progress-message');
                lp_bug_entry = updated_entry;

                // XXX noodles 2009-03-17 bug=336866 It seems the etag
                // returned by lp_save() is incorrect. Remove it for now
                // so that the second save does not result in a '412
                // precondition failed' error.
                lp_bug_entry.removeAtt('http_etag');

                var privacy_div = Y.get('#privacy');
                if (private) {
                    privacy_div.removeClass('public');
                    privacy_div.addClass('private');
                    privacy_text.set(
                        'innerHTML',
                        'This report is <strong>private</strong> ');
                } else {
                    privacy_div.removeClass('private');
                    privacy_div.addClass('public');
                    privacy_text.set(
                        'innerHTML', 'This report is public ');
                }
                privacy_text.appendChild(privacy_link);

                var security_message = Y.get('#security-message');
                if (security_related) {
                    if (security_message === null) {
                        var security_message_html = [
                            '<div style="',
                            '    margin-top: 0.5em;',
                            '    padding-right: 18px;',
                            '    background:url(/@@/security)',
                            '    center right no-repeat;"',
                            '    id="security-message"',
                            '>Security vulnerability</div>'
                        ].join('');
                        security_message = Y.Node.create(security_message_html);
                        privacy_div.appendChild(security_message);
                    }
                } else {
                    if (security_message !== null) {
                        privacy_div.removeChild(security_message);
                    }
                }
                Y.lazr.anim.green_flash({node: privacy_div}).run();
            },
            failure: function(id, request) {
                privacy_text.removeClass('update-in-progress-message');
                Y.lazr.anim.red_flash({node: privacy_div}).run();
                privacy_form_overlay.showError(request.responseText);
                privacy_form_overlay.show();
            }
        }
    };
    lp_bug_entry.lp_save(config);
};

/*
 * Create the form overlay to use when encountering errors.
 *
 * @method create_error_overlay
*/
function create_error_overlay() {
    error_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Error</h2>',
        form_content:  '',
        form_submit_button: Y.Node.create(
            '<button style="display:none"></button>'),
        form_cancel_button: cancel_form_button(),
        centered: true,
        visible: false
    });
    error_overlay.render();
}

/*
 * Create a form button for canceling an error form
 * that won't reload the page on submit.
 *
 * @method cancel_form_button
 * @return button {object} The form's cancel button.
*/
function cancel_form_button() {
    var button = Y.Node.create('<button>OK</button>');
    button.on('click', function(e) {
        e.preventDefault();
        error_overlay.hide();
    });
    return button;
}

/*
 * Take an error message and display in an overlay.
 *
 * @method display_error
 * @param flash_node {object} The node to red flash.
 * @param msg {string} The message to display.
*/
function display_error(flash_node, msg) {
    if (flash_node) {
        var anim = Y.lazr.anim.red_flash({ node: flash_node });
        anim.on('end', function(e) {
            error_overlay.showError(msg);
            error_overlay.show();
        });
        anim.run();
    } else {
        error_overlay.showError(msg);
        error_overlay.show();
    }
}

/*
 * Unsubscribe the current user from this bugtask
 * when the minus icon is clicked.
 *
 * @method unsubscribe_user_via_icon
 * @param icon {object} The minus icon that was clicked.
 * @param subscription_link {object} The subscribe/unsubscribe user link.
*/
function unsubscribe_user_via_icon(icon, subscription_link) {
    remove_user_name_link();
    add_user_name_link();
    icon.set('src', '/@@/spinner');

    var config = {
        on: {
            success: function(client) {
                var icon_parent = icon.get('parentNode');
                icon_parent.removeChild(icon);

                subscription_link.set('innerHTML', 'Subscribe');
                subscription_link.setStyle('background',
                    'url(/@@/add) left center no-repeat');

                var flash_node = Y.get('#subscriber-' + short_name);
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.on('end', function(e) {
                    var me_node = Y.get('#subscriber-' + short_name);
                    var parent = me_node.get('parentNode');
                    parent.removeChild(me_node);
                });
                anim.run();
            },

            failure: function(some_int, response, args) {
                icon.set('src', '/@@/remove');
                // Grab the icon again to reset to click handler.
                var unsubscribe_icon = Y.get(
                    '#unsubscribe-icon-' + me.substring(2));
                unsubscribe_icon.on('click', function(e) {
                    e.halt();
                    unsubscribe_user_via_icon(e.target, subscription_link);
                });

                var flash_node = Y.get('#subscriber-' + short_name);
                var msg = 'There was an error in unsubscribing. ' +
                    'Please wait a little and try again.';
                display_error(flash_node, msg);
            }
        },
        parameters: {
        }
    }
    lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
}

function remove_user_name_link() {
    var me_node = Y.get('#subscriber-' + short_name);
    var parent = me_node.get('parentNode');
    parent.removeChild(me_node);
}

function add_user_name_link() {
    var html = [
        '<div id="subscriber-' + short_name + '">',
        '<a href="' + me + '" title="Subscribed themselves">',
        '<img alt="" src="/@@/person" width="14" height="14" />',
        '&nbsp;' + display_name + '</a>',
        '<a href="+subscribe" style="float: right;',
        ' margin-top: -17px" id="unsubscribe-' + short_name,
        '" title="Unsubscribe ' + display_name + '">',
        '<img src="/@@/remove" id="unsubscribe-icon-',
        short_name + '" />',
        '</a></div>'
    ].join('');
    var link_node = Y.Node.create(html);
    var subscribers = Y.get('#subscribers-links');
    subscribers.insertBefore(link_node,
        subscribers.get('firstChild'));
}

/*
 * Subscribe the current user via the LP API.
 *
 * @method subscribe_current_user
 * @param subscription_link {object} The subscribe link that was clicked.
 */
function subscribe_current_user(subscription_link) {
    subscription_link.setStyle('display', 'none');
    spinner.set('innerHTML', 'Subscribing...');
    spinner.setStyle('display', 'block');

    var config = {
        on: {
            success: function(client) {
                spinner.setStyle('display', 'none');
                subscription_link.set('innerHTML', 'Unsubscribe');
                subscription_link.setStyle('background',
                    'url(/@@/remove) left center no-repeat');
                subscription_link.setStyle('display', 'block');

                var html = [
                    '<div id="subscriber-' + short_name + '">',
                    '<a href="' + me + '" title="Subscribed themselves">',
                    '<img alt="" src="/@@/person" width="14" height="14" />',
                    '&nbsp;' + display_name + '</a>',
                    '<a href="+subscribe" style="float: right;',
                    ' margin-top: -17px" id="unsubscribe-' + short_name,
                    '" title="Unsubscribe ' + display_name + '">',
                    '<img src="/@@/remove" id="unsubscribe-icon-',
                    short_name + '" />',
                    '</a></div>'
                ].join('');
                var link_node = Y.Node.create(html);
                var subscribers = Y.get('#subscribers-links');
                subscribers.insertBefore(link_node,
                    subscribers.get('firstChild'));

                // Set up the click handler for this newly added
                // unsubscribe minus icon.
                var unsubscribe_icon = Y.get('#unsubscribe-icon-' + short_name);
                if (unsubscribe_icon) {
                    unsubscribe_icon.on('click', function(e) {
                        e.halt();
                        unsubscribe_user_via_icon(e.target, subscription_link);
                    });
                }

                var flash_node = Y.get('#subscriber-' + short_name);
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.run();
            },

            failure: function(some_int, response, args) {
                spinner.setStyle('display', 'none');
                subscription_link.setStyle('display', 'block');
                var msg = 'There was an error in subscribing. ' +
                    'Please wait a little and try again.';
                display_error(subscription_link, msg);
            }
        },

        parameters: {
            person: LP.client.get_absolute_uri(me)
        }
    }
    lp_client.named_post(bug_repr.self_link, 'subscribe', config);
}

/*
 * Unsubscribe the current user via the LP API.
 *
 * @method unsubscribe_current_user
 * @param subscription_link {object} The unsubscribe link that was clicked.
 */
function unsubscribe_current_user(subscription_link) {
    subscription_link.setStyle('display', 'none');
    spinner.set('innerHTML', 'Unsubscribing...');
    spinner.setStyle('display', 'block');

    var config = {
        on: {
            success: function(client) {
                spinner.setStyle('display', 'none');
                subscription_link.set('innerHTML', 'Subscribe');
                subscription_link.setStyle('background',
                    'url(/@@/add) left center no-repeat');
                subscription_link.setStyle('display', 'block');

                var flash_node = Y.get('#subscriber-' + short_name);
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.on('end', function(e) {
                    var me_node = Y.get('#subscriber-' + short_name);
                    var parent = me_node.get('parentNode');
                    parent.removeChild(me_node);
                });
                anim.run();
            },

            failure: function(some_int, response, args) {
                spinner.setStyle('display', 'none');
                subscription_link.setStyle('display', 'block');
                var msg = 'There was an error in unsubscribing. ' +
                    'Please wait a little and try again.';
                display_error(subscription_link, msg);
            }
        },

        parameters: {
        }
    }
    lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
}

}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'io-base',
                      'lazr.formoverlay', 'lazr.anim']});
