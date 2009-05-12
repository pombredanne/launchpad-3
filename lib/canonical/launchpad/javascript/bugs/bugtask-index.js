/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Form overlay widgets and subscriber handling for bug pages.
 *
 * @module BugtaskIndex
 * @requires base, node, lazr.formoverlay, lazr.anim
 */

YUI.add('bugs.bugtask_index', function(Y) {

var bugs = Y.namespace('bugs');

// lazr.FormOverlay objects.
var duplicate_form_overlay;
var privacy_form_overlay;

// The url of the page used to update bug duplicates.
var update_dupe_url;

// The launchpad js client used.
var lp_client;

// The initially hidden subscription spinner element.
var spinner;

// The launchpad client entry for the current bug.
var lp_bug_entry;

// The bug itself, taken from cache.
var bug_repr;

// Below are all pertinent to current user.
var me; // A URI.
var short_name;
var display_name;

// Overlay related vars.
var error_overlay;
var form_load_callbacks = {};
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';
var privacy_link;
var privacy_spinner;

/*
 * An object representing the bugtask subscribers portlet.
 *
 * Since the portlet loads via XHR and inline subscribing
 * depends on that portlet being loaded, setup a custom
 * event object, to provide a hook for initializing subscription
 * link callbacks after a bugs:portletloaded event.
 *
 * XXX deryck 2009-04-30 bug=369874 Now this object exists,
 * the inline js on bug-portlet-subscribers.pt should be moved here.
*/
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
Y.bugs.portlet = new PortletTarget();
Y.bugs.portlet.subscribe('bugs:portletloaded', function() {
    setup_subscription_link_handlers();
});

Y.bugs.setup_bugtask_index = function() {
    /*
     * Check the page for links related to overlay forms and request the HTML
     * for these forms.
     */
    Y.on('load', function() {
        if (Y.UA.ie) {
            return;
        }
        // If the user is not logged in, then we need to defer to the
        // default behaviour.
        if (LP.client.links.me === undefined) {
            return;
        }

        if (lp_client === undefined || bug_repr === undefined) {
            setup_client_and_bug();
        }

        if (me === undefined) {
            setup_names();
        }

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
            var privacy_html = privacy_link.get('innerHTML') + ' ';
            privacy_div.set('innerHTML', privacy_html);
            var privacy_text = Y.get('#privacy-text');
            privacy_link = Y.Node.create(
                '<a href="' + privacy_link_url + '" id="privacy-link">' +
                '<img src="/@@/edit"></a>');
            privacy_text.appendChild(privacy_link);
            privacy_spinner = Y.Node.create(
                '<img src="/@@/spinner" style="display: none" />');
            privacy_text.appendChild(privacy_spinner);
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
    }, window);
};

/*
 * Initialize callbacks for subscribe/unsubscribe links.
 *
 * @method setup_subscription_link_handlers
 */
function setup_subscription_link_handlers() {
    if (LP.client.links.me === undefined) {
        return;
    }

    if (lp_client === undefined || bug_repr === undefined) {
        setup_client_and_bug();
    }

    if (me === undefined) {
        setup_names();
    }

    spinner = Y.get('#sub-unsub-spinner');

    var subscription_link = Y.get('.menu-link-subscription');
    if (subscription_link) {
        subscription_link.on('click', function(e) {
            e.halt();
            if (e.target.get('parentNode').hasClass('subscribed-false')) {
                subscribe_current_user(e.target);
            }
            else {
                unsubscribe_current_user(e.target);
            }
        });
        subscription_link.addClass('js-action');
    }

    // The unsubscribe icon in the scribers list has to be
    // handled uniquely.
    var unsubscribe_icon = Y.get('#unsubscribe-icon-' + user_name);
    if (unsubscribe_icon) {
        unsubscribe_icon.on('click', function(e) {
            e.halt();
            unsubscribe_user_via_icon(e.target, subscription_link);
        });
    }

    create_error_overlay();
}

/*
 * Create the lp client and bug entry if we haven't done so already.
 *
 * @method setup_client_and_bug
 */
function setup_client_and_bug() {
    lp_client = new LP.client.Launchpad();

    if (bug_repr === undefined) {
        bug_repr = LP.client.cache.bug;
        lp_bug_entry = new LP.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);
    }
}

/*
 * Initialize the various variables for referring to "me".
 *
 * @method setup_names
 */
function setup_names() {
    me = LP.client.links.me;
    // To get the actual user name, strip the leading "/~"
    // from the "me" URI.
    user_name = me.substring(2);
    config = {
        on: {
            success: function(person) {
                display_name = person.lookup_value('display_name');
            },
            failure: function(args) {
                display_error(null, 'Could not find your account.');
            }
        }
    };
    lp_client.get(me, config);
}

/*
 * Creates the duplicate form overlay using the passed form content.
 *
 * @method createBugDuplicateFormOverlay
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
    // XXX noodles 2009-03-17 bug=336866 It seems the etag
    // returned by lp_save() is incorrect. Remove it for now
    // so that the second save does not result in a '412
    // precondition failed' error.
    //
    // XXX deryck 2009-04-29 bug=369293 Also, this has to
    // happen before *any* call to lp_save now that bug
    // subscribing can be done inline.  Named operations
    // don't return new objects, making the cached bug's
    // etag invalid as well.
    lp_bug_entry.removeAtt('http_etag');

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

                if (new_dup_url !== null) {
                    dupe_span.set('innerHTML', [
                        'Duplicate of <a href="/bugs/' + new_dup_id + '">',
                        'bug #' + new_dup_id +'</a> ',
                        '<a class="menu-link-mark-dupe js-action" ',
                        'href="' + update_dupe_url + '">',
                        '<img src="/@@/edit" /></a>'
                        ].join(''));
                    show_comment_on_duplicate_warning();
                } else {
                    dupe_span.set('innerHTML',
                        '<a class="menu-link-mark-dupe js-action" href="' +
                        update_dupe_url + '">' +
                        '<img src="/@@/bug-dupe-icon" /> ' +
                        'Mark as duplicate</a>');
                    hide_comment_on_duplicate_warning();
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
 * Ensure that a warning about adding a comment to a duplicate bug
 * is displayed.
 *
 * @method show_comment_on_duplicate_warning
 */
var show_comment_on_duplicate_warning = function() {
    var duplicate_warning = Y.get('#warning-comment-on-duplicate');
    if (duplicate_warning === null) {
        var container = Y.get('#new-comment');
        var first_node = container.get('firstChild');
        duplicate_warning = Y.Node.create(
            ['<div class="warning message" id="warning-comment-on-duplicate">',
             'Remember, this bug report is a duplicate. ',
             'Comment here only if you think the duplicate status is wrong.',
             '</div>'].join(''));
        container.insertBefore(duplicate_warning, first_node);
    }
};

/*
 * Ensure that no warning about adding a comment to a duplicate bug
 * is displayed.
 *
 * @method hide_comment_on_duplicate_warning
 */
var hide_comment_on_duplicate_warning = function() {
    var duplicate_warning = Y.get('#warning-comment-on-duplicate');
    if (duplicate_warning !== null) {
        duplicate_warning.ancestor().removeChild(duplicate_warning);
    }
};


/*
 * Create the privacy settings form overlay.
 *
 * @method create_privacy_form_overlay
 * @param form_content {String} The HTML data of the form overlay.
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
    // XXX noodles 2009-03-17 bug=336866 It seems the etag
    // returned by lp_save() is incorrect. Remove it for now
    // so that the second save does not result in a '412
    // precondition failed' error.
    //
    // XXX deryck 2009-04-29 bug=369293 Also, this has to
    // happen before *any* call to lp_save now that bug
    // subscribing can be done inline.  Named operations
    // don't return new objects, making the cached bug's
    // etag invalid as well.
    lp_bug_entry.removeAtt('http_etag');

    privacy_form_overlay.hide();

    var privacy_text = Y.get('#privacy-text');
    var privacy_div = Y.get('#privacy');
    privacy_link.setStyle('display', 'none');
    privacy_spinner.setStyle('display', 'inline');

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
                privacy_spinner.setStyle('display', 'none');
                privacy_link.setStyle('display', 'inline');
                lp_bug_entry = updated_entry;

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
                privacy_text.appendChild(privacy_spinner);

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
                privacy_spinner.setStyle('display', 'none');
                privacy_link.setStyle('display', 'inline');
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
 * @return button {Node} The form's cancel button.
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
 * @param flash_node {Node} The node to red flash.
 * @param msg {String} The message to display.
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
 * Used to remove the user's name from the subscriber's list.
 * This fixes a bug where the div for the user name does not flash
 * green as it should.
 *
 * @method remove_user_name_link
 */
function remove_user_name_link() {
    var me_node = Y.get('#subscriber-' + user_name);
    var parent = me_node.get('parentNode');
    parent.removeChild(me_node);
}

/*
 * Add the user name to the subscriber's list.
 *
 * @method add_user_name_link
 */
function add_user_name_link() {
    var html = [
        '<div id="subscriber-' + user_name + '">',
        '<a href="' + me + '" title="Subscribed themselves">',
        '<img alt="" src="/@@/person" width="14" height="14" />',
        '&nbsp;' + display_name + '</a>',
        '<a href="+subscribe" style="float: right;',
        ' margin-top: -17px" id="unsubscribe-' + user_name,
        '" title="Unsubscribe ' + display_name + '">',
        '<img src="/@@/remove" id="unsubscribe-icon-',
        user_name + '" />',
        '</a></div>'
    ].join('');
    var link_node = Y.Node.create(html);
    var subscribers = Y.get('#subscribers-links');
    subscribers.insertBefore(link_node,
        subscribers.get('firstChild'));
}

/*
 * Add the "None" div to the subscribers list if
 * there aren't any subscribers left.
 *
 * @method set_none_for_empty_subscribers
 */
function set_none_for_empty_subscribers() {
    var subscriber_list = Y.get('#subscribers-links');
    // Assume if subscriber_list has no child divs
    // then the list of subscribers is empty.
    if (!subscriber_list.query('div')) {
        var none_div = Y.Node.create('<div id="none-subscribers">None</div>');
        subscriber_list.appendChild(none_div);
    }
}

/*
 * Set the class on subscription link's parentNode.
 *
 * This is used to reset the class used by the
 * click handler to know which link was clicked.
 *
 * @method set_subscription_link_parent_class
 * @param subscription_link {Node} The sub/unsub link.
 * @param subscribed {Boolean} The sub/unsub'ed flag for the class.
 */
function set_subscription_link_parent_class(subscription_link, subscribed) {
    var parent = subscription_link.get('parentNode');
    parent.setAttribute('class', 'subscribed-' + subscribed);
}

/*
 * Unsubscribe the current user from this bugtask
 * when the minus icon is clicked.
 *
 * @method unsubscribe_user_via_icon
 * @param icon {Node} The minus icon that was clicked.
 * @param subscription_link {Node} The subscribe/unsubscribe user link.
*/
function unsubscribe_user_via_icon(icon, subscription_link) {
    icon.set('src', '/@@/spinner');

    var config = {
        on: {
            success: function(client) {
                var icon_parent = icon.get('parentNode');
                icon_parent.removeChild(icon);
                remove_user_name_link();
                add_user_name_link();

                // Checking for a subscription link here helps this degrade
                // better when landing on +subscribe pages accidentally.
                if (subscription_link) {
                    subscription_link.set('innerHTML', 'Subscribe');
                    subscription_link.setStyle('background',
                        'url(/@@/add) left center no-repeat');
                    set_subscription_link_parent_class(subscription_link, false);
                }

                var flash_node = Y.get('#subscriber-' + user_name);
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.on('end', function(e) {
                    var me_node = Y.get('#subscriber-' + user_name);
                    var parent = me_node.get('parentNode');
                    parent.removeChild(me_node);
                    set_none_for_empty_subscribers();
                });
                anim.run();
            },

            failure: function(some_int, response, args) {
                icon.set('src', '/@@/remove');
                remove_user_name_link();
                add_user_name_link();
                // Grab the icon again to reset to click handler.
                var unsubscribe_icon = Y.get(
                    '#unsubscribe-icon-' + user_name);
                unsubscribe_icon.on('click', function(e) {
                    e.halt();
                    unsubscribe_user_via_icon(e.target, subscription_link);
                });

                var flash_node = Y.get('#subscriber-' + user_name);
                var msg = 'There was an error in unsubscribing. ' +
                    'Please wait a little and try again.';
                display_error(flash_node, msg);
            }
        },
        parameters: {
        }
    };
    lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
}

/*
 * Subscribe the current user via the LP API.
 *
 * @method subscribe_current_user
 * @param subscription_link {Node} The subscribe link that was clicked.
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
                set_subscription_link_parent_class(subscription_link, true);

                // Handle the case where the subscriber's list displays "None".
                var empty_subscribers = Y.get("#none-subscribers");
                if (empty_subscribers) {
                    var parent = empty_subscribers.get('parentNode');
                    parent.removeChild(empty_subscribers);
                }

                var html = [
                    '<div id="subscriber-' + user_name + '">',
                    '<a href="' + me + '" title="Subscribed themselves">',
                    '<img alt="" src="/@@/person" width="14" height="14" />',
                    '&nbsp;' + display_name + '</a>',
                    '<a href="+subscribe" style="float: right;',
                    ' margin-top: -17px" id="unsubscribe-' + user_name,
                    '" title="Unsubscribe ' + display_name + '">',
                    '<img src="/@@/remove" id="unsubscribe-icon-',
                    user_name + '" />',
                    '</a></div>'
                ].join('');
                var link_node = Y.Node.create(html);
                var subscribers = Y.get('#subscribers-links');
                subscribers.insertBefore(link_node,
                    subscribers.get('firstChild'));

                // Set up the click handler for this newly added
                // unsubscribe minus icon.
                var unsubscribe_icon = Y.get('#unsubscribe-icon-' + user_name);
                if (unsubscribe_icon) {
                    unsubscribe_icon.on('click', function(e) {
                        e.halt();
                        unsubscribe_user_via_icon(e.target, subscription_link);
                    });
                }

                var flash_node = Y.get('#subscriber-' + user_name);
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
    };
    lp_client.named_post(bug_repr.self_link, 'subscribe', config);
}

/*
 * Unsubscribe the current user via the LP API.
 *
 * @method unsubscribe_current_user
 * @param subscription_link {Node} The unsubscribe link that was clicked.
 */
function unsubscribe_current_user(subscription_link) {
    subscription_link.setStyle('display', 'none');
    spinner.set('innerHTML', 'Unsubscribing...');
    spinner.setStyle('display', 'block');

    var config = {
        on: {
            success: function(client) {
                remove_user_name_link();
                add_user_name_link();
                spinner.setStyle('display', 'none');
                subscription_link.set('innerHTML', 'Subscribe');
                subscription_link.setStyle('background',
                    'url(/@@/add) left center no-repeat');
                subscription_link.setStyle('display', 'block');
                set_subscription_link_parent_class(subscription_link, false);

                var flash_node = Y.get('#subscriber-' + user_name);
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.on('end', function(e) {
                    var me_node = Y.get('#subscriber-' + user_name);
                    var parent = me_node.get('parentNode');
                    parent.removeChild(me_node);
                    set_none_for_empty_subscribers();
                });
                anim.run();
            },

            failure: function(some_int, response, args) {
                remove_user_name_link();
                add_user_name_link();
                spinner.setStyle('display', 'none');
                subscription_link.setStyle('display', 'block');
                var msg = 'There was an error in unsubscribing. ' +
                    'Please wait a little and try again.';
                display_error(subscription_link, msg);
            }
        },

        parameters: {
        }
    };
    lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
}

}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'io-base',
                      'lazr.formoverlay', 'lazr.anim']});
