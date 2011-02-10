/* Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Form overlay widgets and subscriber handling for bug pages.
 *
 * @module bugs
 * @submodule bugtask_index
 */

YUI.add('lp.bugs.bugtask_index', function(Y) {

var namespace = Y.namespace('lp.bugs.bugtask_index');

// lazr.FormOverlay objects.
var duplicate_form_overlay;
var privacy_form_overlay;

// The url of the page used to update bug duplicates.
var update_dupe_url;

// The launchpad js client used.
var lp_client;

// The launchpad client entry for the current bug.
var lp_bug_entry;

// The bug itself, taken from cache.
var bug_repr;

// Overlay related vars.
var error_overlay;
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';
var privacy_link;
var privacy_spinner;
var link_branch_link;

// The set of subscriber CSS IDs as a JSON struct.
var subscriber_ids;

// A boolean telling us whether advanced subscription features are to be
// used or not.
// XXX 2011-01-14 gmb bug=702859:
//     We need to expose feature flags via the API to avoid this kind of
//     thing.
var use_advanced_subscriptions = false;
var subscription_labels = Y.lp.bugs.subscriber.subscription_labels;

/*
 * An object representing the bugtask subscribers portlet.
 *
 * Since the portlet loads via XHR and inline subscribing
 * depends on that portlet being loaded, setup a custom
 * event object, to provide a hook for initializing subscription
 * link callbacks after custom events.
 */
var PortletTarget = function() {};
Y.augment(PortletTarget, Y.Event.Target);
namespace.portlet = new PortletTarget();

function setup_portlet_handlers() {
    namespace.portlet.subscribe('bugs:portletloaded', function() {
        load_subscriber_ids();
    });
    namespace.portlet.subscribe('bugs:dupeportletloaded', function() {
        setup_unsubscribe_icon_handlers();
    });
    /*
     * If the subscribers portlet fails to load, clear any
     * click handlers, so the normal subscribe page can be reached.
     */
    namespace.portlet.subscribe('bugs:portletloadfailed', function(handlers) {
        if (Y.Lang.isArray(handlers)) {
            var click_handler = handlers[0];
            click_handler.detach();
        }
    });
    /* If the dupe subscribers portlet fails to load,
     * be sure to try to handle any unsub icons that may
     * exist for others.
     */
    namespace.portlet.subscribe(
        'bugs:dupeportletloadfailed',
        function(handlers) {
            setup_unsubscribe_icon_handlers();
        });

    /* If loading the subscriber IDs JSON has succeeded, set up the
     * subscription link handlers and load the subscribers from dupes.
     */
    namespace.portlet.subscribe(
        'bugs:portletsubscriberidsloaded',
        function() {
            setup_subscription_link_handlers();
            load_subscribers_from_duplicates();
        });

    /* If loading the subscriber IDs JSON fails we still need to load the
     * subscribers from duplicates but we don't set up the subscription link
     * handlers.
     */
    namespace.portlet.subscribe(
        'bugs:portletsubscriberidsfailed',
        function() {
            load_subscribers_from_duplicates();
        });

    /*
     * Subscribing someone else requires loading a grayed out
     * username into the DOM until the subscribe action completes.
     * There are a couple XHR requests in check_can_be_unsubscribed
     * before the subscribe work can be done, so fire a custom event
     * bugs:nameloaded and do the work here when the event fires.
     */
    namespace.portlet.subscribe('bugs:nameloaded', function(subscription) {
        var error_handler = new LP.client.ErrorHandler();
        error_handler.clearProgressUI = function() {
            var temp_link = Y.one('#temp-username');
            if (temp_link) {
                var temp_parent = temp_link.get('parentNode');
                temp_parent.removeChild(temp_link);
            }
        };
        error_handler.showError = function(error_msg) {
            Y.lp.app.errors.display_error(
                Y.one('.menu-link-addsubscriber'), error_msg);
        };

        var config = {
            on: {
                success: function() {
                    var temp_link = Y.one('#temp-username');
                    var temp_spinner = Y.one('#temp-name-spinner');
                    temp_link.removeChild(temp_spinner);
                    var anim = Y.lazr.anim.green_flash({ node: temp_link });
                    anim.on('end', function() {
                        add_user_name_link(subscription);
                        var temp_parent = temp_link.get('parentNode');
                        temp_parent.removeChild(temp_link);
                    });
                    anim.run();
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                person: LP.client.get_absolute_uri(
                    subscription.get('person').get('escaped_uri')),
                suppress_notify: false
            }
        };
        lp_client.named_post(bug_repr.self_link, 'subscribe', config);
    });
}

namespace.setup_bugtask_index = function() {
    setup_portlet_handlers();
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

        setup_client_and_bug();

        // Look for the 'Mark as duplicate' links or the
        // 'change duplicate bug' link.
        var update_dupe_link = Y.one(
            '.menu-link-mark-dupe, #change_duplicate_bug');

        if (update_dupe_link) {
            // First things first, pre-load the mark-dupe form.
            update_dupe_url = update_dupe_link.get('href');
            var mark_dupe_form_url = update_dupe_url + '/++form++';

            var form_header = '<p>Marking this bug as a duplicate will,' +
                              ' by default, hide it from search results ' +
                              'listings.</p>';

            var has_dupes = Y.one('#portlet-duplicates');
            if (has_dupes !== null) {
                form_header = form_header +
                    '<p style="padding:2px 2px 0 36px;" ' +
                    'class="large-warning"><strong>Note:</strong> ' +
                    'This bug has duplicates of its own. ' +
                    'If you go ahead, they too will become duplicates of ' +
                    'the bug you specify here.  This cannot be undone.' +
                    '</p></div>';
            }

            duplicate_form_overlay = new Y.lazr.FormOverlay({
                headerContent: '<h2>Mark bug report as duplicate</h2>',
                form_header: form_header,
                form_submit_button: Y.Node.create(submit_button_html),
                form_cancel_button: Y.Node.create(cancel_button_html),
                centered: true,
                form_submit_callback: update_bug_duplicate,
                visible: false
            });
            duplicate_form_overlay.render('#duplicate-form-container');
            duplicate_form_overlay.loadFormContentAndRender(
                mark_dupe_form_url);

            // Add an on-click handler to any links found that displays
            // the form overlay.
            update_dupe_link.on('click', function(e) {
                // Only go ahead if we have received the form content by the
                // time the user clicks:
                if (duplicate_form_overlay){
                    e.preventDefault();
                    duplicate_form_overlay.show();
                    Y.DOM.byId('field.duplicateof').focus();
                }
            });
            // Add a class denoting them as js-action links.
            update_dupe_link.addClass('js-action');
        }

        privacy_link = Y.one('#privacy-link');

        if (privacy_link) {
            var privacy_link_url = privacy_link.getAttribute('href') +
              '/++form++';
            var privacy_div = Y.one('#privacy-text');
            var privacy_html = privacy_link.get('innerHTML') + ' ';
            privacy_div.set('innerHTML', privacy_html);
            var privacy_text = Y.one('#privacy-text');
            privacy_link = Y.Node.create(
                '<a id="privacy-link" class="sprite edit" title="[edit]">' +
                '<span class="invisible-link">edit</span>&nbsp;</a>');
            privacy_link.set('href', privacy_link_url);
            privacy_text.appendChild(privacy_link);
            privacy_spinner = Y.Node.create(
                '<img src="/@@/spinner" style="display: none" />');
            privacy_text.appendChild(privacy_spinner);


            privacy_form_overlay = new Y.lazr.FormOverlay({
                headerContent: '<h2>Change privacy settings</h2>',
                form_submit_button: Y.Node.create(submit_button_html),
                form_cancel_button: Y.Node.create(cancel_button_html),
                centered: true,
                form_submit_callback: update_privacy_settings,
                visible: false
            });
            privacy_form_overlay.render('#privacy-form-container');
            privacy_form_overlay.loadFormContentAndRender(privacy_link_url);
            privacy_link.on('click', function(e) {
                if (privacy_form_overlay) {
                    e.preventDefault();
                    privacy_form_overlay.show();
                    // XXX Abel Deuring 2009-04-23, bug 365462
                    // Y.one('#field.private') returns null.
                    // Seems that YUI does not like IDs containing a '.'
                    document.getElementById('field.private').focus();
                }
            });
            privacy_link.addClass('js-action');
        }
        setup_add_attachment();
        setup_link_branch_picker();
    }, window);
};


/*
 * Initialize click handler for the subscribe someone else link.
 *
 * @method setup_subscribe_someone_else_handler
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function setup_subscribe_someone_else_handler(subscription) {
    var config = {
        header: 'Subscribe someone else',
        step_title: 'Search',
        picker_activator: '.menu-link-addsubscriber'
    };

    config.save = function(result) {
        subscribe_someone_else(result, subscription);
    };
    var picker = Y.lp.app.picker.create('ValidPersonOrTeam', config);
}


/*
 * Handle the advanced_subscription_overlay's form submissions.
 *
 * @method handle_advanced_subscription_overlay
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 * @param form_data {Object} The data from the submitted form.
 */
function handle_advanced_subscription_overlay(subscription, form_data) {
    var link = subscription.get('link');
    var link_parent = link.get('parentNode');
    if (link_parent.hasClass('subscribed-false') &&
        link_parent.hasClass('dup-subscribed-false')) {
        // The user isn't subscribed, so subscribe them.
        subscription.set(
            'bug_notification_level',
            form_data['field.bug_notification_level']);
        subscribe_current_user(subscription);
    } else if (
        form_data['field.subscription'] == 'update-subscription') {
        // The user is already subscribed and wants to update their
        // subscription.
        setup_client_and_bug();
        var person_name = subscription.get('person').get('name');
        var subscription_url =
            lp_bug_entry.get('self_link') + '/+subscription/' +
            person_name;
        config = {
            on: {
                success: function(lp_subscription) {
                    subscription.enable_spinner('Updating subscription...');
                    lp_subscription.set(
                        'bug_notification_level',
                        form_data['field.bug_notification_level'][0])
                    save_config = {
                        on: {
                            success: function(e) {
                                subscription.disable_spinner(
                                    'Edit subscription');
                                var anim = Y.lazr.anim.green_flash({
                                    node: link_parent
                                    });
                                anim.run();
                            },
                            failure: function(e) {
                                subscription.disable_spinner(
                                    'Edit subscription');
                                var anim = Y.lazr.anim.red_flash({
                                    node: link_parent
                                    });
                                anim.run();
                            }
                        }
                    }
                    lp_subscription.lp_save(save_config);
                }
            }
        }
        lp_client.get(subscription_url, config);
    } else {
        // The user is already subscribed and wants to unsubscribe.
        unsubscribe_current_user(subscription);
    }
}


/*
 * Create and return a FormOverlay for advanced subscription
 * interactions.
 *
 * @method setup_advanced_subscription_overlay
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function setup_advanced_subscription_overlay(subscription) {
    var subscription_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Subscribe to bug</h2>',
        form_submit_button:
            Y.Node.create(submit_button_html),
        form_cancel_button:
            Y.Node.create(cancel_button_html),
        centered: true,
        visible: false
    });
    subscription_overlay.set(
        'form_submit_callback', function(form_data) {
        handle_advanced_subscription_overlay(subscription, form_data);
        subscription_overlay.hide();
    });

    var subscription_link_url = subscription.get(
        'link').get('href') + '/++form++';
    subscription_overlay.loadFormContentAndRender(
        subscription_link_url);
    subscription_overlay.render('#privacy-form-container');
    return subscription_overlay
}


/*
 * Initialize callbacks for subscribe/unsubscribe links.
 *
 * @method setup_subscription_link_handlers
 */
function setup_subscription_link_handlers() {
    if (LP.client.links.me === undefined) {
        return;
    }

    setup_client_and_bug();
    var subscription = new Y.lp.bugs.subscriber.Subscription({
        link: Y.one('.menu-link-subscription'),
        spinner: Y.one('#sub-unsub-spinner'),
        subscriber: new Y.lp.bugs.subscriber.Subscriber({
            uri: LP.client.links.me,
            subscriber_ids: subscriber_ids
        })
    });

    var is_direct = subscription.get(
        'link').get('parentNode').hasClass('subscribed-true');
    var has_dupes = subscription.get(
        'link').get('parentNode').hasClass('dup-subscribed-true');
    subscription.set('is_direct', is_direct);
    subscription.set('has_dupes', has_dupes);

    if (subscription.is_node()) {
        subscription.get('link').on('click', function(e) {
            e.halt();
            subscription.set('can_be_unsubscribed', true);
            subscription.set('person', subscription.get('subscriber'));
            subscription.set('is_team', false);
            var parent = e.target.get('parentNode');
            if (namespace.use_advanced_subscriptions) {
                var subscription_overlay =
                    setup_advanced_subscription_overlay(subscription);
                subscription_overlay.show();
            } else {
                // Look for the false conditions of subscription, which
                // is_direct_subscription, etc. don't report correctly,
                // to make sure we only use subscribe_current_user for
                // the current user.
                if (parent.hasClass('subscribed-false') &&
                    parent.hasClass('dup-subscribed-false')) {
                    subscribe_current_user(subscription);
                }
                else {
                    unsubscribe_current_user(subscription);
                }
            }
        });
        subscription.get('link').addClass('js-action');
    }

    setup_subscribe_someone_else_handler(subscription);
}

/*
 * Set click handlers for unsubscribe remove icons.
 *
 * @method setup_unsubscribe_icon_handlers
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function setup_unsubscribe_icon_handlers() {
    var subscription = new Y.lp.bugs.subscriber.Subscription({
        link: Y.one('.menu-link-subscription'),
        spinner: Y.one('#sub-unsub-spinner'),
        subscriber: new Y.lp.bugs.subscriber.Subscriber({
            uri: LP.client.links.me,
            subscriber_ids: subscriber_ids
        })
    });

    Y.on('click', function(e) {
        e.halt();
        unsubscribe_user_via_icon(e.target, subscription);
    }, '.unsub-icon');
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
    lp_bug_entry.removeAttr('http_etag');

    // Hide the formoverlay:
    duplicate_form_overlay.hide();

    // Hide the dupe edit icon if it exists.
    var dupe_edit_icon = Y.one('#change_duplicate_bug');
    if (dupe_edit_icon !== null) {
        dupe_edit_icon.setStyle('display', 'none');
    }

    // Add the spinner...
    var dupe_span = Y.one('#mark-duplicate-text');
    dupe_span.removeClass('sprite bug-dupe');
    dupe_span.addClass('update-in-progress-message');

    // Set the new duplicate link on the bug entry.
    var new_dup_url = null;
    var new_dup_id = Y.Lang.trim(data['field.duplicateof'][0]);
    if (new_dup_id !== '') {
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
                        '<a id="change_duplicate_bug" ',
                        'title="Edit or remove linked duplicate bug" ',
                        'class="sprite edit"></a>',
                        'Duplicate of <a>bug #</a>'].join(""));
                    dupe_span.all('a').item(0)
                        .set('href', update_dupe_url);
                    dupe_span.all('a').item(1)
                        .set('href', '/bugs/' + new_dup_id)
                        .appendChild(document.createTextNode(new_dup_id));
                    var has_dupes = Y.one('#portlet-duplicates');
                    if (has_dupes !== null) {
                        has_dupes.get('parentNode').removeChild(has_dupes);
                    }
                    show_comment_on_duplicate_warning();
                } else {
                    dupe_span.addClass('sprite bug-dupe');
                    dupe_span.set('innerHTML', [
                        '<a class="menu-link-mark-dupe js-action">',
                        'Mark as duplicate</a>'].join(""));
                    dupe_span.one('a').set('href', update_dupe_url);
                    hide_comment_on_duplicate_warning();
                }
                Y.lazr.anim.green_flash({node: dupe_span}).run();
                // ensure the new link is hooked up correctly:
                dupe_span.one('a').on(
                    'click', function(e){
                        e.preventDefault();
                        duplicate_form_overlay.show();
                        Y.DOM.byId('field.duplicateof').focus();
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
    var duplicate_warning = Y.one('#warning-comment-on-duplicate');
    if (duplicate_warning === null) {
        var container = Y.one('#add-comment-form');
        var first_node = container.get('firstChild');
        duplicate_warning = Y.Node.create(
            ['<div class="warning message"',
             'id="warning-comment-on-duplicate">',
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
    var duplicate_warning = Y.one('#warning-comment-on-duplicate');
    if (duplicate_warning !== null) {
        duplicate_warning.ancestor().removeChild(duplicate_warning);
    }
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
    lp_bug_entry.removeAttr('http_etag');

    privacy_form_overlay.hide();

    var privacy_text = Y.one('#privacy-text');
    var privacy_div = Y.one('#privacy');
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

    var private_flag = data['field.private'] !== undefined;
    var security_related =
        data['field.security_related'] !== undefined;

    lp_bug_entry.set('private', private_flag);
    lp_bug_entry.set('security_related', security_related);
    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        privacy_spinner.setStyle('display', 'none');
        privacy_link.setStyle('display', 'inline');
    };
    error_handler.showError = function (error_msg) {
        Y.lazr.anim.red_flash({node: privacy_div}).run();
        privacy_form_overlay.showError(error_msg);
        privacy_form_overlay.show();
    };

    var config = {
        on: {
            success: function (updated_entry) {
                privacy_spinner.setStyle('display', 'none');
                privacy_link.setStyle('display', 'inline');
                lp_bug_entry = updated_entry;

                if (private_flag) {
                    Y.one('body').replaceClass('public', 'private');
                    privacy_div.replaceClass('public', 'private');
                    privacy_text.set(
                        'innerHTML',
                        'This report is <strong>private</strong> ');
                } else {
                    Y.one('body').replaceClass('private', 'public');
                    privacy_div.replaceClass('private', 'public');
                    privacy_text.set(
                        'innerHTML', 'This report is public ');
                }
                privacy_text.appendChild(privacy_link);
                privacy_text.appendChild(privacy_spinner);

                var security_message = Y.one('#security-message');
                if (security_related) {
                    if (security_message === null) {
                        var security_message_html = [
                            '<div style="',
                            '    margin-top: 0.5em;',
                            '    padding-right: 18px;',
                            '    center right no-repeat;"',
                            '    class="sprite security"',
                            '    id="security-message"',
                            '>Security vulnerability</div>'
                        ].join('');
                        security_message = Y.Node.create(
                           security_message_html);
                        privacy_div.appendChild(security_message);
                    }
                } else {
                    if (security_message !== null) {
                        privacy_div.removeChild(security_message);
                    }
                }
                Y.lazr.anim.green_flash({node: privacy_div}).run();
            },
            failure: error_handler.getFailureHandler()
        }
    };
    lp_bug_entry.lp_save(config);
};


/**
 * Set up the link-a-related-branch picker.
 */
function setup_link_branch_picker() {
    setup_client_and_bug();

    var error_handler = new LP.client.ErrorHandler();

    error_handler.clearProgressUI = function () {
        link_branch_link.toggleClass('update-in-progress-message');
    };
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
           Y.one('.menu-link-addbranch'), error_msg);
    };

    function get_branch_and_link_to_bug(data) {
        var branch_url = data.api_uri;
        config = {
            on: {
                success: link_branch_to_bug,
                failure: error_handler.getFailureHandler()
            }
        };

        // Start the spinner and then grab the branch.
        link_branch_link.toggleClass('update-in-progress-message');
        lp_client.get(branch_url, config);
    }

    // Set up the picker itself.
    link_branch_link = Y.one('.menu-link-addbranch');
    if (Y.Lang.isValue(link_branch_link)) {
        var config = {
            header: 'Link a related branch',
            step_title: 'Search',
            picker_activator: '.menu-link-addbranch'
        };

        config.save = get_branch_and_link_to_bug;
        var picker = Y.lp.app.picker.create('Branch', config);
    }
}

/**
 * Link a branch to the current bug.
 * @param branch {Object} The branch to link to the bug, as returned by
 *                        the Launchpad API.
 */
function link_branch_to_bug(branch) {
    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        link_branch_link.toggleClass('update-in-progress-message');
    };
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
           Y.one('.menu-link-addbranch'), error_msg);
    };

    // Call linkBranch() on the bug.
    config = {
        on: {
            success: function(bug_branch_entry) {
                link_branch_link.toggleClass(
                    'update-in-progress-message');

                // Grab the XHTML representation of the branch and add
                // it to the list of branches.
                config = {
                    on: {
                        success: function(branch_html) {
                            add_branch_to_linked_branches(branch_html);
                        }
                    },
                    accept: LP.client.XHTML
                };
                lp_client.get(bug_branch_entry.get('self_link'), config);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            branch: branch.get('self_link')
        }
    };
    lp_client.named_post(
        lp_bug_entry.get('self_link'), 'linkBranch', config);
}

/**
 * Add a branch to the list of linked branches.
 *
 * @param branch_html {Object} The branch html to add to the list of
 *                    linked branches, as returned by the Launchpad API.
 */
function add_branch_to_linked_branches(branch_html) {
    var anim;
    var bug_branch_node = Y.Node.create(branch_html);
    var bug_branch_list = Y.one('#bug-branches');
    if (!Y.Lang.isValue(bug_branch_list)) {
        bug_branch_list = Y.Node.create(
            '<div id="bug-branches">' +
            '  <h2>Related branches</h2>' +
            '</div>');

        var bug_branch_container = Y.one('#bug-branches-container');
        bug_branch_container.appendChild(bug_branch_list);
        anim = Y.lazr.anim.green_flash({node: bug_branch_list});
    } else {
        anim = Y.lazr.anim.green_flash({node: bug_branch_node});
    }

    var existing_bug_branch_node = bug_branch_list.one(
        '#' + bug_branch_node.getAttribute('id'));
    if (!Y.Lang.isValue(existing_bug_branch_node)) {
        // Only add the bug branch to the page if it isn't there
        // already.
        bug_branch_list.appendChild(bug_branch_node);
    } else {
        // If the bug branch exists already, flash it.
        anim = Y.lazr.anim.green_flash({node: existing_bug_branch_node});
    }
    anim.run();
    // Fire of the generic branch linked event.
    Y.fire('lp:branch-linked', bug_branch_node);
}

/*
 * Traverse the DOM of a given remove icon to find
 * the user's link.  Returns a URI of the form "/~username".
 *
 * @method get_user_uri_from_icon
 * @param icon {Node} The node representing a remove icon.
 * @return user_uri {String} The user's uri, without the hostname.
 */
function get_user_uri_from_icon(icon) {
    var parent_div = icon.get('parentNode').get('parentNode');
    // This should be parent_div.firstChild, but because of #text
    // and cross-browser issues, using the YUI query syntax is
    // safer here.
    var user_uri = parent_div.one('a').getAttribute('href');

    // Strip the domain off. We just want a path.
    var host_start = user_uri.indexOf('//');
    if (host_start != -1) {
        var host_end = user_uri.indexOf('/', host_start+2);
        return user_uri.substring(host_end, user_uri.length);
    }

    return user_uri;
}


/*
 * Build the HTML for a user link for the subscribers list.
 *
 * @method build_user_link_html
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 * @return html {String} The HTML used for creating a subscriber link.
 */
function build_user_link_html(subscription) {
    var name = subscription.get('person').get('name');
    var css_name = subscription.get('person').get('css_name');
    var full_name = subscription.get('person').get('full_display_name');
    // Be paranoid about display_name, since timeouts or other errors
    // could mean display_name wasn't set on initialization.
    if (subscription.get('person').get('display_name') === '') {
        subscription.get('person').set_display_name();
    }
    var display_name = subscription.get('person').get('display_name');
    var terms = {
        name: name,
        css_name: css_name,
        display_name: display_name,
        full_name: full_name
    };

    if (subscription.is_current_user_subscribing()) {
        terms.subscribed_by = 'themselves';
    } else {
        terms.subscribed_by = 'by ' + full_name;
    }

    var html = Y.Node.create('<div><a></a></div>');
    html.addClass(terms.css_name);

    if (subscription.is_direct_subscription()) {
        html.set('id', 'direct-' + terms.css_name);
    } else {
        html.set('id', 'dupe-' + terms.css_name);
    }

    html.one('a')
        .set('href', '/~' + terms.name)
        .set('name', terms.full_name)
        .set('title', 'Subscribed ' + terms.subscribed_by);

    var span;
    if (subscription.is_team()) {
        span = '<span class="sprite team"></span>';
    } else {
        span = '<span class="sprite person"></span>';
    }

    html.one('a')
        .appendChild(Y.Node.create(span))
        .appendChild(document.createTextNode(terms.display_name));

    // Add remove icon if the current user can unsubscribe the subscriber.
    if (subscription.can_be_unsubscribed_by_user()) {
        var icon_html = Y.Node.create(
            '<a href="+subscribe">' +
            '<img class="unsub-icon" src="/@@/remove" /></a>');
        icon_html
            .set('id', 'unsubscribe-' + terms.css_name)
            .set('title', 'Unsubscribe ' + terms.full_name);
        icon_html.one('img')
            .set('id', 'unsubscribe-icon-' + terms.css_name);
        html.appendChild(icon_html);
    }

    return html;
}

/*
 * Used to remove the user's name from the subscriber's list.
 *
 * @method remove_user_name_link
 * @param user_node {Node} Node representing the user name link.
 */
function remove_user_name_link(user_node) {
    var parent = user_node.get('parentNode');
    parent.removeChild(user_node);
}

/*
 * Returns the next node in alphabetical order after the subscriber
 * node now being added.  No node is returned to append to end of list.
 *
 * The name can appear in one of two different lists. 1) The list of
 * subscribers that can be unsubscribed by the current user, and
 * 2) the list of subscribers that cannont be unsubscribed.
 *
 * @method get_next_subscriber_node
 * @param subscription_link {Node} The sub/unsub link.
 * @return {Node} The node appearing next in the subscriber list or
 *          undefined if no node is next.
 */
function get_next_subscriber_node(subscription) {
    var full_name = subscription.get('person').get('full_display_name');
    var can_be_unsubscribed = subscription.can_be_unsubscribed_by_user();
    var nodes_by_name = {};
    var unsubscribables = [];
    var not_unsubscribables = [];

    // Use the list of subscribers pulled from the DOM to have sortable
    // lists of unsubscribable vs. not unsubscribale person links.
    var all_subscribers = Y.all('#subscribers-links div');
    if (all_subscribers.size() > 0) {
        all_subscribers.each(function(sub_link) {
            if (sub_link.getAttribute('id') != 'temp-username') {
                // User's displayname is found via the link's "name"
                // attribute.
                var sub_link_name = sub_link.one('a').getAttribute('name');
                nodes_by_name[sub_link_name] = sub_link;
                if (sub_link.one('img.unsub-icon')) {
                    unsubscribables.push(sub_link_name);
                } else {
                    not_unsubscribables.push(sub_link_name);
                }
            }
        });

        // Add the current subscription.
        if (can_be_unsubscribed) {
            unsubscribables.push(full_name);
        } else {
            not_unsubscribables.push(full_name);
        }
        unsubscribables.sort();
        not_unsubscribables.sort();
    } else {
        // If there is no all_subscribers, then we're dealing with
        // the printed None, so return.
        return;
    }

    var i;
    if ((!unsubscribables && !not_unsubscribables) ||
        // If A) neither list exists, B) the user belongs in the second
        // list but the second list doesn't exist, or C) user belongs in the
        // first list and the second doesn't exist, return no node to append.
        (!can_be_unsubscribed && !not_unsubscribables) ||
        (can_be_unsubscribed && unsubscribables && !not_unsubscribables)) {
        return;
    } else if (
        // If the user belongs in the first list, and the first list
        // doesn't exist, but the second one does, return the first node
        // in the second list.
        can_be_unsubscribed && !unsubscribables && not_unsubscribables) {
        return nodes_by_name[not_unsubscribables[0]];
    } else if (can_be_unsubscribed) {
        // If the user belongs in the first list, loop the list for position.
        for (i=0; i<unsubscribables.length; i++) {
            if (unsubscribables[i] == full_name) {
                if (i+1 < unsubscribables.length) {
                    return nodes_by_name[unsubscribables[i+1]];
                // If the current link should go at the end of the first
                // list and we're at the end of that list, return the
                // first node of the second list.  Due to earlier checks
                // we can be sure this list exists.
                } else if (i+1 >= unsubscribables.length) {
                    return nodes_by_name[not_unsubscribables[0]];
                }
            }
        }
    } else if (!can_be_unsubscribed) {
        // If user belongs in the second list, loop the list for position.
        for (i=0; i<not_unsubscribables.length; i++) {
            if (not_unsubscribables[i] == full_name) {
                if (i+1 < not_unsubscribables.length) {
                    return nodes_by_name[not_unsubscribables[i+1]];
                } else {
                    return;
                }
            }
        }
    }
}

/*
 * Add the user name to the subscriber's list.
 *
 * @method add_user_name_link
 */
function add_user_name_link(subscription) {
    var person = subscription.get('person');
    var link_node = build_user_link_html(subscription);
    var subscribers = Y.one('#subscribers-links');
    if (subscription.is_current_user_subscribing()) {
        // If this is the current user, then top post the name and be done.
        subscribers.insertBefore(link_node, subscribers.get('firstChild'));
    } else {
        var next = get_next_subscriber_node(subscription);
        if (next) {
            subscribers.insertBefore(link_node, next);
        } else {
            // Handle the case of the displayed "None".
            var none_subscribers = Y.one('#none-subscribers');
            if (none_subscribers) {
                var none_parent = none_subscribers.get('parentNode');
                none_parent.removeChild(none_subscribers);
            }
            subscribers.appendChild(link_node);
        }
    }

    // Set the click handler if adding a remove icon.
    if (subscription.can_be_unsubscribed_by_user()) {
        var remove_icon =
          Y.one('#unsubscribe-icon-' + person.get('css_name'));
        remove_icon.on('click', function(e) {
            e.halt();
            unsubscribe_user_via_icon(e.target, subscription);
        });
    }
}

/*
 * Add a grayed out, temporary user name when subscribing
 * someone else.
 *
 * @method add_temp_user_name
 * @param subscription_link {Node} The sub/unsub link.
 */
function add_temp_user_name(subscription) {
    // Be paranoid about display_name, since timeouts or other errors
    // could mean display_name wasn't set on initialization.
    if (subscription.get('person').get('display_name') === '') {
        subscription.get('person').set_display_name();
    }
    var display_name = subscription.get('person').get('display_name');
    var img_src;
    if (subscription.is_team()) {
        img_src = '/@@/teamgray';
    } else {
        img_src = '/@@/persongray';
    }

    // The <span>...</span> below must *not* be <span/>. On FF (maybe
    // others, but at least on FF 3.0.11) will then not notice any
    // following sibling nodes, like the spinner image.
    var link_node = Y.Node.create([
        '<div id="temp-username"> ',
        '  <img alt="" width="14" height="14" />',
        '  <span>Other Display Name</span>',
        '  <img id="temp-name-spinner" src="/@@/spinner" alt="" ',
        '       style="position:absolute;right:8px" /></div>'].join(''));
    link_node.one('img').set('src', img_src);
    link_node.replaceChild(
        document.createTextNode(display_name),
        link_node.one('span'));

    var subscribers = Y.one('#subscribers-links');
    var next = get_next_subscriber_node(subscription);
    if (next) {
        subscribers.insertBefore(link_node, next);
    } else {
        // Handle the case of the displayed "None".
        var none_subscribers = Y.one('#none-subscribers');
        if (none_subscribers) {
            var none_parent = none_subscribers.get('parentNode');
            none_parent.removeChild(none_subscribers);
        }
        subscribers.appendChild(link_node);
    }

    // Fire a custom event to know it's safe to begin
    // any actual subscribing work.
    namespace.portlet.fire('bugs:nameloaded', subscription);
}

/*
 * Add the "None" div to the subscribers list if
 * there aren't any subscribers left.
 *
 * @method set_none_for_empty_subscribers
 */
function set_none_for_empty_subscribers() {
    var subscriber_list = Y.one('#subscribers-links');
    // Assume if subscriber_list has no child divs
    // then the list of subscribers is empty.
    if (!Y.Lang.isValue(subscriber_list.one('div')) &&
        !Y.Lang.isValue(Y.one('#none-subscribers'))) {
        var none_div = Y.Node.create('<div id="none-subscribers">None</div>');
        subscriber_list.appendChild(none_div);
    }

    // Clear the empty duplicate subscribers list if it exists.
    var dup_list = Y.one('#subscribers-from-duplicates');
    if (Y.Lang.isValue(dup_list) &&
        !Y.Lang.isValue(dup_list.one('div'))) {
        var parent = dup_list.get('parentNode');
        parent.removeChild(dup_list);
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
 * @param dupe_subscribed {Boolean} The sub/unsub'ed flag for dupes
 *                                  on the class.
 */
function set_subscription_link_parent_class(
    user_link, subscribed, dupe_subscribed) {

    var parent = user_link.get('parentNode');
    if (subscribed) {
        parent.removeClass('subscribed-false');
        parent.addClass('subscribed-true');
    } else {
        parent.removeClass('subscribed-true');
        parent.addClass('subscribed-false');
    }

    if (dupe_subscribed) {
        parent.removeClass('dup-subscribed-false');
        parent.addClass('dup-subscribed-true');
    } else {
        parent.removeClass('dup-subscribed-true');
        parent.addClass('dup-subscribed-false');
    }
}

/*
 * Unsubscribe a user from this bugtask when a remove icon is clicked.
 *
 * @method unsubscribe_user_via_icon
 * @param icon {Node} The remove icon that was clicked.
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
*/
function unsubscribe_user_via_icon(icon, subscription) {
    icon.set('src', '/@@/spinner');
    var icon_parent = icon.get('parentNode');

    var user_uri = get_user_uri_from_icon(icon);
    var person = new Y.lp.bugs.subscriber.Subscriber({
        uri: user_uri,
        subscriber_ids: subscriber_ids
    });
    subscription.set('person', person);

    // Determine if this is a dupe.
    var is_dupe;
    var icon_parent_div = icon_parent.get('parentNode');
    var dupe_id = 'dupe-' + person.get('css_name');
    if (icon_parent_div.get('id') == dupe_id) {
        is_dupe = true;
    } else {
        is_dupe = false;
    }

    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        icon.set('src', '/@@/remove');
        // Grab the icon again to reset to click handler.
        var unsubscribe_icon = Y.one(
            '#unsubscribe-icon-' + person.get('css_name'));
        unsubscribe_icon.on('click', function(e) {
            e.halt();
            unsubscribe_user_via_icon(e.target, subscription);
        });

    };
    error_handler.showError = function (error_msg) {
        var flash_node = Y.one('.' + person.get('css_name'));
        Y.lp.app.errors.display_error(flash_node, error_msg);

    };

    var subscription_link = subscription.get('link');
    var config = {
        on: {
            success: function(client) {
                icon_parent.removeChild(icon);
                var anim = Y.lazr.anim.green_flash({ node: icon_parent_div });
                anim.on('end', function(e) {
                    remove_user_name_link(icon_parent_div);
                    set_none_for_empty_subscribers();
                    var person_link = Y.one('.' + person.get('css_name'));
                    if (Y.Lang.isNull(person_link) &&
                        subscription.is_current_user_subscribing()) {
                            // Current user has been completely unsubscribed.
                            subscription.disable_spinner(
                                subscription_labels.SUBSCRIBE);
                            set_subscription_link_parent_class(
                                subscription_link, false, false);
                            subscription.set('is_direct', false);
                            subscription.set('has_dupes', false);
                    } else {
                        if (is_dupe) {
                            // A direct subscription remains.
                            set_subscription_link_parent_class(
                                subscription_link, true, false);
                            subscription.set('is_direct', true);
                            subscription.set('has_dupes', false);
                        } else {
                            // A dupe subscription remains.
                            set_subscription_link_parent_class(
                                subscription_link, false, true);
                            subscription.set('is_direct', false);
                            subscription.set('has_dupes', true);
                        }
                    }
                });
                anim.run();
            },

            failure: error_handler.getFailureHandler()
        }
    };

    if (!subscription.is_current_user_subscribing()) {
        config.parameters = {
            person: LP.client.get_absolute_uri(user_uri)
        };
    }

    if (is_dupe) {
        lp_client.named_post(
            bug_repr.self_link, 'unsubscribeFromDupes', config);
    } else {
        lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
    }
}

/*
 * Subscribe the current user via the LP API.
 *
 * @method subscribe_current_user
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function subscribe_current_user(subscription) {
    subscription.enable_spinner('Subscribing...');
    var subscription_link = subscription.get('link');
    var subscriber = subscription.get('subscriber');
    var bug_notification_level = subscription.get('bug_notification_level');

    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        subscription.disable_spinner();
    };
    error_handler.showError = function (error_msg) {
        Y.lp.app.errors.display_error(subscription_link, error_msg);
    };

    var config = {
        on: {
            success: function(client) {
                if (namespace.use_advanced_subscriptions) {
                    subscription.disable_spinner(
                        subscription_labels.EDIT);
                } else {
                    subscription.disable_spinner(
                        subscription_labels.UNSUBSCRIBE);
                }

                if (subscription.has_duplicate_subscriptions()) {
                    set_subscription_link_parent_class(
                        subscription_link, true, true);
                } else {
                    set_subscription_link_parent_class(
                        subscription_link, true, false);
                }

                // Handle the case where the subscriber's list displays
                // "None".
                var empty_subscribers = Y.one("#none-subscribers");
                if (empty_subscribers) {
                    var parent = empty_subscribers.get('parentNode');
                    parent.removeChild(empty_subscribers);
                }

                add_user_name_link(subscription);

                var flash_node = Y.one('.' + subscriber.get('css_name'));
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.run();
            },

            failure: error_handler.getFailureHandler()
        },

        parameters: {
            person: LP.client.get_absolute_uri(subscriber.get('escaped_uri')),
            suppress_notify: false,
            level: bug_notification_level
        }
    };
    lp_client.named_post(bug_repr.self_link, 'subscribe', config);
}

/*
 * Unsubscribe the current user via the LP API.
 *
 * @method unsubscribe_current_user
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function unsubscribe_current_user(subscription) {
    subscription.enable_spinner('Unsubscribing...');
    var subscription_link = subscription.get('link');
    var subscriber = subscription.get('subscriber');

    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        subscription.disable_spinner();
    };
    error_handler.showError = function (error_msg) {
        Y.lp.app.errors.display_error(subscription_link, error_msg);
    };

    var config = {
        on: {
            success: function(client) {
                if (subscription.is_direct_subscription() &&
                    subscription.has_duplicate_subscriptions()) {
                    // Don't change the 'Unsubscribe' text if
                    // dupe subscriptions remain.
                    subscription.disable_spinner();
                    set_subscription_link_parent_class(
                        subscription_link, false, true);
                    subscription.set('is_direct', false);
                } else if (subscription.is_direct_subscription() &&
                          !subscription.has_duplicate_subscriptions()) {
                    // Only unsub'ing a direct subscriber here.
                    subscription.disable_spinner(
                        subscription_labels.SUBSCRIBE);
                    set_subscription_link_parent_class(
                        subscription_link, false, false);
                    subscription.set('is_direct', false);
                } else {
                    // Only unsub'ing dupes here.
                    subscription.disable_spinner(
                        subscription_labels.SUBSCRIBE);
                    set_subscription_link_parent_class(
                        subscription_link, false, false);
                    subscription.set('has_dupes', false);
                }

                var flash_node = Y.one('.' + subscriber.get('css_name'));
                var anim = Y.lazr.anim.green_flash({ node: flash_node });
                anim.on('end', function(e) {
                    remove_user_name_link(flash_node);
                    set_none_for_empty_subscribers();
                });
                anim.run();
            },

            failure: error_handler.getFailureHandler()
        }
    };
    if (subscription.is_direct_subscription()) {
        lp_client.named_post(bug_repr.self_link, 'unsubscribe', config);
    } else {
        lp_client.named_post(
            bug_repr.self_link, 'unsubscribeFromDupes', config);
    }
}


/**
 * Set up a bug task table row.
 *
 * Called once, on load, to initialize the page.
 *
 * @method setup_bugtasks_row
 */
namespace.setup_bugtask_row = function(conf) {
    if (Y.UA.ie) {
        return;
    }

    var tr = Y.one('#' + conf.row_id);
    var bugtarget_content = Y.one('#bugtarget-picker-' + conf.row_id);
    var status_content = tr.one('.status-content');
    var importance_content = tr.one('.importance-content');
    var assignee_content = Y.one('#assignee-picker-' + conf.row_id);
    var milestone_content = tr.one('.milestone-content');

    if (status_content === null) {
        // Not all table rows have status widgets.  If this is one of those
        // rows, then bail.
        return;
    }

    if (Y.Lang.isValue(LP.client.cache.bug) &&
        Y.Lang.isValue(LP.client.cache.bug.duplicate_of_link)) {
        // If the bug is a duplicate, don't set the widget up and
        // canel clicks on the edit links. Users most likely don't
        // want to edit the bugtasks.
        status_content.on('click', function(e) { e.halt(); });
        importance_content.on('click', function(e) { e.halt(); });
        return;
    }

    if ((LP.client.links.me !== undefined) &&
        (LP.client.links.me !== null))  {
        if (Y.Lang.isValue(bugtarget_content)) {
            if (conf.target_is_product) {
              var bugtarget_picker = Y.lp.app.picker.addPickerPatcher(
                        'Product',
                        conf.bugtask_path,
                        "target_link",
                        bugtarget_content.get('id'),
                        {"step_title": "Search products",
                         "header": "Change product"});
            }
        }

        if (conf.user_can_edit_status) {
            var status_choice_edit = new Y.ChoiceSource({
                contentBox: status_content,
                value: conf.status_value,
                title: 'Change status to',
                items: conf.status_widget_items,
                elementToFlash: status_content.get('parentNode'),
                backgroundColor:
                    tr.hasClass('highlight') ? '#FFFF99' : '#FFFFFF'
            });
            status_choice_edit.showError = function(err) {
              Y.lp.app.errors.display_error(null, err);
            };
            status_choice_edit.on('save', function(e) {
                var cb = status_choice_edit.get('contentBox');
                Y.Array.each(conf.status_widget_items, function(item) {
                    if (item.value == status_choice_edit.get('value')) {
                        cb.addClass(item.css_class);
                    } else {
                        cb.removeClass(item.css_class);
                    }
                });
                // Set the inline form control's value, so that submitting
                // it won't override the value we just set.
                Y.one(document.getElementById(conf.prefix + '.status')).set(
                    'value', status_choice_edit.get('value'));
            });
            status_choice_edit.plug({
                fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                        patch: 'status',
                        resource: conf.bugtask_path}});
            status_choice_edit.render();
        }
        if (conf.user_can_edit_importance) {
            var importance_choice_edit = new Y.ChoiceSource({
                contentBox: importance_content,
                value: conf.importance_value,
                title: 'Change importance to',
                items: conf.importance_widget_items,
                elementToFlash: importance_content.get('parentNode'),
                backgroundColor:
                    tr.hasClass('highlight') ? '#FFFF99' : '#FFFFFF'
            });
            importance_choice_edit.showError = function(err) {
              Y.lp.app.errors.display_error(null, err);
            };
            importance_choice_edit.on('save', function(e) {
                var cb = importance_choice_edit.get('contentBox');
                Y.Array.each(conf.importance_widget_items, function(item) {
                    if (item.value == importance_choice_edit.get('value')) {
                        cb.addClass(item.css_class);
                    } else {
                        cb.removeClass(item.css_class);
                    }
                });
                // Set the inline form control's value, so that submitting
                // it won't override the value we just set.
                Y.one(document.getElementById(
                    conf.prefix + '.importance')).set(
                        'value', importance_choice_edit.get('value'));
            });
            importance_choice_edit.plug({
                fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                        patch: 'importance',
                        resource: conf.bugtask_path}});
            importance_choice_edit.render();
        }
    }

    if (Y.Lang.isValue(milestone_content) && conf.user_can_edit_milestone) {
        var milestone_choice_edit = new Y.NullChoiceSource({
            contentBox: milestone_content,
            value: conf.milestone_value,
            title: 'Target to milestone',
            items: conf.milestone_widget_items,
            elementToFlash: milestone_content.get('parentNode'),
            backgroundColor: tr.hasClass('highlight') ? '#FFFF99' : '#FFFFFF',
            clickable_content: false
        });
        milestone_choice_edit.showError = function(err) {
            Y.lp.app.errors.display_error(null, err);
        };
        milestone_choice_edit.plug({
            fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                    patch: 'milestone_link',
                    resource: conf.bugtask_path}});
        milestone_choice_edit.after('save', function() {
            var new_value = milestone_choice_edit.get('value');
            if (Y.Lang.isValue(new_value)) {
                // XXX Tom Berger 2009-08-25 Bug #316694:
                // This is a slightly nasty hack that saves us from the need
                // to have a more established way of getting the web URL of
                // an API object. Once such a solution is available we should
                // fix this.
                milestone_content.one('.value').setAttribute(
                    'href', new_value.replace('/api/devel', ''));
            }
            // Set the inline form control's value, so that submitting
            // it won't override the value we just set.
            var inline_combo = Y.one(
                document.getElementById(conf.prefix + '.milestone'));
            if (Y.Lang.isValue(inline_combo)) {
            inline_combo.set('value', null);
                Y.Array.each(
                   milestone_choice_edit.get('items'), function(item) {
                    if (item.value == milestone_choice_edit.get('value')) {
                        inline_combo.all('option').each(function(opt) {
                            if (opt.get('innerHTML') == item.name) {
                                opt.set('selected', true);
                            }
                        });
                    }
                });
            }
            // Force redrawing the UI
            milestone_choice_edit._uiClearWaiting();
        });
        milestone_content.one('.nulltext').on(
            'click',
            milestone_choice_edit.onClick,
            milestone_choice_edit);
        milestone_choice_edit.render();
    }
    if (Y.Lang.isValue(assignee_content)) {
        var step_title =
            (conf.assignee_vocabulary == 'ValidAssignee') ?
            "Search for people or teams" :
            "Select a team of which you are a member";
        var assignee_picker = Y.lp.app.picker.addPickerPatcher(
            conf.assignee_vocabulary,
            conf.bugtask_path,
            "assignee_link",
            assignee_content.get('id'),
            {"step_title": step_title,
             "header": "Change assignee",
             "remove_button_text": "Remove assignee",
             "null_display_value": "Unassigned",
             "show_remove_button": conf.user_can_unassign,
             "show_assign_me_button": true});
        // Ordinary users can select only themselves and their teams.
        // Do not show the team selection, if a user is not a member
        // of any team,
        if (conf.hide_assignee_team_selection) {
            content_box = assignee_picker.get('contentBox');
            search_box = content_box.one('.yui-picker-search-box');
            search_box.setStyle('display', 'none');
            step_title = content_box.one('.contains-steptitle');
            step_title.setStyle('display', 'none');
        }
        assignee_picker.render();
    }
};

/**
 * Set up the "me too" selection.
 *
 * Called once, on load, to initialize the page. Call this function if
 * the "me too" information is displayed on a bug page and the user is
 * logged in.
 *
 * @method setup_me_too
 */
namespace.setup_me_too = function(user_is_affected, others_affected_count) {
    // IE (7 & 8 tested) is stupid, stupid, stupid.
    if (Y.UA.ie) {
        return;
    }
    var me_too_content = Y.one('#affectsmetoo');
    var me_too_edit = new MeTooChoiceSource({
        contentBox: me_too_content, value: user_is_affected,
        elementToFlash: me_too_content,
        editicon: ".dynamic img.editicon",
        others_affected_count: others_affected_count
    });
    me_too_edit.render();
};

/**
 * This class is a derivative of ChoiceSource that handles the
 * specifics of editing "me too" option.
 *
 * @class MeTooChoiceSource
 * @extends ChoiceSource
 * @constructor
 */
function MeTooChoiceSource() {
    MeTooChoiceSource.superclass.constructor.apply(this, arguments);
}

MeTooChoiceSource.NAME = 'metoocs';
MeTooChoiceSource.NS = 'metoocs';

MeTooChoiceSource.ATTRS = {
    /**
     * The title is always the same, so bake it in here.
     *
     * @attribute title
     * @type String
     */
    title: {
        value: 'Does this bug affect you?'
    },

    /**
     * The items are always the same, so bake them in here.
     *
     * @attribute items
     * @type Array
     */
    items: {
        value: [
            { name: 'Yes, it affects me',
              value: true, disabled: false },
            { name: "No, it doesn't affect me",
              value: false, disabled: false }
        ]
    },

    /**
     * The number of other users currently affected by this bug.
     *
     * @attribute others_affected_count
     * @type Number
     */
    others_affected_count: {
        value: null
    }
};

// Put this in the bugs namespace so it can be accessed for testing.
namespace._MeTooChoiceSource = MeTooChoiceSource;

Y.extend(MeTooChoiceSource, Y.ChoiceSource, {
    initializer: function() {
        var widget = this;
        this.error_handler = new LP.client.ErrorHandler();
        this.error_handler.clearProgressUI = function() {
            widget._uiClearWaiting();
        };
        this.error_handler.showError = function(error_msg) {
            widget.showError(error_msg);
        };
        // Set source_names.
        var others_affected_count = this.get('others_affected_count');
        var source_names = this._getSourceNames(others_affected_count);
        Y.each(this.get('items'), function(item) {
            if (item.value in source_names) {
                item.source_name = source_names[item.value];
            }
        });
    },

    /*
     * The results of _getSourceNames() should closely mirror the
     * results of BugTasksAndNominationsView.affected_statement and
     * anon_affected_statement.
     */
    _getSourceNames: function(others_affected_count) {
        var source_names = {};
        // What to say when the user is marked as affected.
        if (others_affected_count == 1) {
            source_names[true] = (
                'This bug affects you and 1 other person');
        }
        else if (others_affected_count > 1) {
            source_names[true] = (
                'This bug affects you and ' +
                others_affected_count + ' other people');
        }
        else {
            source_names[true] = 'This bug affects you';
        }
        // What to say when the user is marked as not affected.
        if (others_affected_count == 1) {
            source_names[false] = (
                'This bug affects 1 person, but not you');
        }
        else if (others_affected_count > 1) {
            source_names[false] = (
                'This bug affects ' + others_affected_count +
                ' people, but not you');
        }
        else {
            source_names[false] = "This bug doesn't affect you";
        }
        return source_names;
    },

    showError: function(err) {
        Y.lp.app.errors.display_error(null, err);
    },

    render: function() {
        MeTooChoiceSource.superclass.render.apply(this, arguments);
        // Force the ChoiceSource to be rendered inline.
        this.get('boundingBox').setStyle('display', 'inline');
        // Hide the static content and show the dynamic content.
        this.get('contentBox').one('.static').addClass('unseen');
        this.get('contentBox').one('.dynamic').removeClass('unseen');
    },

    _saveData: function() {
        // Set the widget to the 'waiting' state.
        this._uiSetWaiting();

        var value = this.getInput();
        var client =  new LP.client.Launchpad();
        var widget = this;

        var config = {
            on: {
                success: function(entry) {
                    widget._uiClearWaiting();
                    MeTooChoiceSource.superclass._saveData.call(
                        widget, value);
                },
                failure: this.error_handler.getFailureHandler()
            },
            parameters: {
                affected: value
            }
        };

        client.named_post(
            LP.client.cache.bug.self_link, 'markUserAffected', config);
    }
});

/*
 * Check if the current user can unsubscribe the person
 * being subscribed.
 *
 * This must be done in JavaScript, since the subscription
 * hasn't completed yet, and so, can_be_unsubscribed_by_user
 * cannot be used.
 *
 * @method check_can_be_unsubscribed
 * @param subscription {Object} A Y.lp.bugs.subscriber.Subscription object.
 */
function check_can_be_unsubscribed(subscription) {
    var error_handler = new LP.client.ErrorHandler();
    error_handler.showError = function (error_msg) {
        Y.lp.app.errors.display_error(
           Y.one('.menu-link-addsubscriber'), error_msg);
    };

    var config = {
        on: {
            success: function(result) {
                var is_team = result.get('is_team');
                subscription.set('is_team', is_team);
                var final_config = {
                    on: {
                        success: function(result) {
                            var team_member = false;
                            for (var i=0; i<result.entries.length; i++) {
                                 if (result.entries[i].member_link ==
                                    LP.client.get_absolute_uri(
                                        subscription.get(
                                            'subscriber').get('uri'))) {
                                    team_member = true;
                                }
                            }

                            if (team_member) {
                                subscription.set('can_be_unsubscribed', true);
                                add_temp_user_name(subscription);
                            } else {
                                subscription.set(
                                   'can_be_unsubscribed', false);
                                add_temp_user_name(subscription);
                            }
                        },

                        failure: error_handler.getFailureHandler()
                    }
                };

                if (is_team) {
                    // Get a list of members to see if current user
                    // is a team member.
                    var members = result.get(
                       'members_details_collection_link');
                    lp_client.get(members, final_config);
                } else {
                    subscription.set('can_be_unsubscribed', false);
                    add_temp_user_name(subscription);
                }
            },

            failure: error_handler.getFailureHandler()
        }
    };
    lp_client.get(LP.client.get_absolute_uri(
        subscription.get('person').get('escaped_uri')), config);
}

/*
 * Subscribe a person or team other than the current user.
 * This is a callback for the subscribe someone else picker.
 *
 * @method subscribe_someone_else
 * @result {Object} The object representing a person returned by the API.
 */
function subscribe_someone_else(result, subscription) {
    var person = new Y.lp.bugs.subscriber.Subscriber({
        uri: result.api_uri,
        display_name: result.title,
        subscriber_ids: subscriber_ids
    });
    subscription.set('person', person);

    var error_handler = new LP.client.ErrorHandler();
    error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(
           Y.one('.menu-link-addsubscriber'), error_msg);
    };

    if (subscription.is_already_subscribed()) {
        error_handler.showError(
             subscription.get('person').get('full_display_name') +
             ' has already been subscribed');
    } else {
        check_can_be_unsubscribed(subscription);
    }
}

/*
 * Click handling to pass comment text to the attachment
 * page if there is a comment.
 *
 * @method setup_add_attachment
 */
function setup_add_attachment() {
    // Find zero or more links to modify.
    var attachment_link = Y.all('.menu-link-addcomment');
    attachment_link.on('click', function(e) {
        var comment_input = Y.one('[id="field.comment"]');
        if (comment_input.get('value') !== '') {
            var current_url = attachment_link.getAttribute('href');
            var attachment_url = current_url + '?field.comment=' +
                encodeURIComponent(comment_input.get('value'));
            attachment_link.setAttribute('href', attachment_url);
        }
    });
}

function load_subscribers_from_duplicates() {
    if (Y.UA.ie) {
        return null;
    }

    Y.one('#subscribers-portlet-dupe-spinner').setStyle(
        'display', 'block');

    function hide_spinner() {
        Y.one('#subscribers-portlet-dupe-spinner').setStyle(
            'display', 'none');
        // Fire a custom event to signal failure, so that
        // any remaining unsub icons can be hooked up.
        namespace.portlet.fire('bugs:dupeportletloadfailed');
    }

    function on_success(transactionid, response, args) {
        hide_spinner();

        var dupe_subscribers_container = Y.one(
            '#subscribers-from-duplicates-container');
        dupe_subscribers_container.set(
            'innerHTML',
            dupe_subscribers_container.get('innerHTML') +
            response.responseText);

        // Fire a custom portlet loaded event to notify when
        // it's safe to setup dupe subscriber link callbacks.
        namespace.portlet.fire('bugs:dupeportletloaded');
    }

    var config = {on: {success: on_success,
                       failure: hide_spinner}};
    var url = Y.one(
        '#subscribers-from-dupes-content-link').getAttribute(
            'href').replace('bugs.', '');
    Y.io(url, config);
}

namespace.load_subscribers_portlet = function(
        subscription_link, subscription_link_handler) {
    if (Y.UA.ie) {
        return null;
    }

    Y.one('#subscribers-portlet-spinner').setStyle('display', 'block');

    function hide_spinner() {
        Y.one('#subscribers-portlet-spinner').setStyle('display', 'none');
            // Fire a custom event to notify that the initial click
            // handler on subscription_link set above should be
            // cleared.
            if (namespace) {
                namespace.portlet.fire(
                  'bugs:portletloadfailed', subscription_link_handler);
        }
    }

    function setup_portlet(transactionid, response, args) {
        hide_spinner();
        var portlet = Y.one('#portlet-subscribers');
        portlet.set('innerHTML',
                    portlet.get('innerHTML') + response.responseText);

        // Fire a custom portlet loaded event to notify when
        // it's safe to setup subscriber link callbacks.
        namespace.portlet.fire('bugs:portletloaded');
    }

    var config = {on: {success: setup_portlet,
                       failure: hide_spinner}};
    var url = Y.one(
        '#subscribers-content-link').getAttribute('href').replace(
            'bugs.', '');
    Y.io(url, config);
};

function load_subscriber_ids() {
    function on_success(transactionid, response, args) {
        try {
            subscriber_ids = Y.JSON.parse(response.responseText);

            // Fire a custom event to trigger the setting-up of the
            // subscription handlers.
            namespace.portlet.fire('bugs:portletsubscriberidsloaded');
        } catch (e) {
            // Fire an event to signal failure. This ensures that the
            // subscribers-from-dupes still get loaded into the portlet.
            namespace.portlet.fire('bugs:portletsubscriberidsfailed');
        }
    }

    function on_failure() {
        // Fire an event to signal failure. This ensures that the
        // subscribers-from-dupes still get loaded into the portlet.
        namespace.portlet.fire('bugs:portletsubscriberidsfailed');
    }

    var config = {on: {success: on_success,
                       failure: on_failure}};
    var url = Y.one(
        '#subscribers-ids-link').getAttribute('href');
    Y.io(url, config);
}

}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "json-parse", "substitute", "widget-position-ext",
                        "lazr.formoverlay", "lazr.anim", "lazr.base",
                        "lazr.overlay", "lazr.choiceedit", "lp.app.picker",
                        "lp.client.plugins", "lp.bugs.subscriber",
                        "lp.app.errors"]});
