/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Form overlay widgets and subscriber handling for bug pages.
 *
 * @module bugs
 * @submodule bugtask_index.portlets
 */

YUI.add('lp.bugs.bugtask_index.portlets', function(Y) {

var namespace = Y.namespace('lp.bugs.bugtask_index.portlets');

// The launchpad js client used.
var lp_client;

// The launchpad client entry for the current bug.
var lp_bug_entry;

// The bug itself, taken from cache.
var bug_repr;

// A boolean telling us whether advanced subscription features are to be
// used or not.
var use_advanced_subscriptions = false;

var subscription_labels = Y.lp.bugs.subscriber.subscription_labels;

submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';

// The set of subscriber CSS IDs as a JSON struct.
var subscriber_ids;

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

/*
 * Create the lp client and bug entry if we haven't done so already.
 *
 * @method setup_client_and_bug
 */
function setup_client_and_bug() {
    lp_client = new Y.lp.client.Launchpad();

    if (bug_repr === undefined) {
        bug_repr = LP.cache.bug;
        lp_bug_entry = new Y.lp.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);
    }
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
        Y.one('#portlet-subscribers')
            .appendChild(Y.Node.create(response.responseText));

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


namespace.setup_portlet_handlers = function() {
    namespace.portlet.subscribe('bugs:portletloaded', function() {
        load_subscriber_ids();
    });
    /*
     * If the subscribers portlet fails to load, clear any
     * click handlers, so the normal subscribe page can be reached.
     */
    namespace.portlet.subscribe('bugs:portletloadfailed', function(handler) {
        handler.detach();
    });
    namespace.portlet.subscribe('bugs:dupeportletloaded', function() {
        setup_subscription_link_handlers();
        setup_unsubscribe_icon_handlers();
    });
    /* If the dupe subscribers portlet fails to load,
     * be sure to try to handle any unsub icons that may
     * exist for others.
     */
    namespace.portlet.subscribe(
        'bugs:dupeportletloadfailed',
        function(handlers) {
            setup_subscription_link_handlers();
            setup_unsubscribe_icon_handlers();
        });

    /* If loading the subscriber IDs JSON has succeeded, set up the
     * subscription link handlers and load the subscribers from dupes.
     */
    namespace.portlet.subscribe(
        'bugs:portletsubscriberidsloaded',
        function() {
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
        var error_handler = new Y.lp.client.ErrorHandler();
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
                person: Y.lp.client.get_absolute_uri(
                    subscription.get('person').get('escaped_uri')),
                suppress_notify: false
            }
        };
        lp_client.named_post(bug_repr.self_link, 'subscribe', config);
    });
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
            uri: LP.links.me,
            subscriber_ids: subscriber_ids
        })
    });

    Y.on('click', function(e) {
        e.halt();
        unsubscribe_user_via_icon(e.target, subscription);
    }, '.unsub-icon');
}

/*
 * Set up and return a Subscription object for the direct subscription
 * link.
 */
function get_subscribe_self_subscription() {
    setup_client_and_bug();
    var subscription = new Y.lp.bugs.subscriber.Subscription({
        link: Y.one('.menu-link-subscription'),
        spinner: Y.one('#sub-unsub-spinner'),
        subscriber: new Y.lp.bugs.subscriber.Subscriber({
            uri: LP.links.me,
            subscriber_ids: subscriber_ids
        })
    });

    subscription.set('can_be_unsubscribed', true);
    subscription.set('person', subscription.get('subscriber'));
    subscription.set('is_team', false);
    var css_name = subscription.get('person').get('css_name');
    var direct_css_name = '#direct-' + css_name;
    var direct_node = Y.one(direct_css_name);
    var is_direct = direct_node !== null;
    subscription.set('is_direct', is_direct);
    var dupe_css_name = '#dupe-' + css_name;
    var dupe_node = Y.one(dupe_css_name);
    var has_dupes = dupe_node !== null;
    subscription.set('has_dupes', has_dupes);
    return subscription;
}


/*
 * Set up and return a Subscription object for the team subscription
 * link.
 */
function get_team_subscription(team_uri) {
    setup_client_and_bug();
    var subscription = new Y.lp.bugs.subscriber.Subscription({
        link: Y.one('.menu-link-subscription'),
        spinner: Y.one('#sub-unsub-spinner'),
        subscriber: new Y.lp.bugs.subscriber.Subscriber({
            uri: team_uri,
            subscriber_ids: subscriber_ids
        })
    });

    subscription.set('is_direct', true);
    subscription.set('has_dupes', false);
    subscription.set('can_be_unsubscribed', true);
    subscription.set('person', subscription.get('subscriber'));
    subscription.set('is_team', true);
    return subscription;
}

/*
 * Initialize callbacks for subscribe/unsubscribe links.
 *
 * @method setup_subscription_link_handlers
 */
function setup_subscription_link_handlers() {
    if (LP.links.me === undefined) {
        return;
    }

    var subscription = get_subscribe_self_subscription();

    setup_subscribe_someone_else_handler(subscription);
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
    }

    function on_failure(transactionid, response, args) {
        hide_spinner();
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
                       failure: on_failure}};
    var url = Y.one(
        '#subscribers-from-dupes-content-link').getAttribute(
            'href').replace('bugs.', '');
    Y.io(url, config);
}

/*
 * Add the user name to the subscriber's list.
 *
 * @method add_user_name_link
 */
function add_user_name_link(subscription) {
    // Be paranoid about display_name, since timeouts or other errors
    // could mean display_name wasn't set on initialization.
    subscription.get('person').set_display_name(function () {
        _add_user_name_link(subscription);
    });
}

function _add_user_name_link(subscription) {
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
            subscribers.appendChild(link_node);
        }
    }
    // Handle the case of no previous subscribers.
    var none_subscribers = Y.one('#none-subscribers');
    if (none_subscribers) {
        var none_parent = none_subscribers.get('parentNode');
        none_parent.removeChild(none_subscribers);
    }
    // Highlight the new addition with a green flash.
    Y.lazr.anim.green_flash({ node: link_node }).run();
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
    if (icon_parent_div.get('id') === dupe_id) {
        is_dupe = true;
    } else {
        is_dupe = false;
    }

    var error_handler = new Y.lp.client.ErrorHandler();
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
                var num_person_links = Y.all(
                    '.' + person.get('css_name')).size();
                Y.lp.bugs.subscribers_list.remove_user_link(person, is_dupe);
                var has_direct, has_dupes;
                if (num_person_links === 1 &&
                    subscription.is_current_user_subscribing()) {
                    // Current user has been completely unsubscribed.
                    subscription.disable_spinner(
                        subscription_labels.SUBSCRIBE);
                    has_direct = false;
                    has_dupes = false;
                } else {
                    // If we removed the duplicate subscription,
                    // we are left with the direct one, and vice versa.
                    has_direct = is_dupe;
                    has_dupes = !is_dupe;
                }
                subscription.set('is_direct', has_direct);
                subscription.set('has_dupes', has_dupes);
                set_subscription_link_parent_class(
                    subscription_link, has_direct, has_dupes);
            },

            failure: error_handler.getFailureHandler()
        }
    };

    if (!subscription.is_current_user_subscribing()) {
        config.parameters = {
            person: Y.lp.client.get_absolute_uri(user_uri)
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

    if (subscription.has_duplicate_subscriptions()) {
        html.set('id', 'dupe-' + terms.css_name);
    } else {
        html.set('id', 'direct-' + terms.css_name);
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
            '<img class="unsub-icon" src="/@@/remove" alt="Remove" /></a>');
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
 * Returns the next node in alphabetical order after the subscriber
 * node now being added.  No node is returned to append to end of list.
 *
 * The name can appear in one of two different lists. 1) The list of
 * subscribers that can be unsubscribed by the current user, and
 * 2) the list of subscribers that cannot be unsubscribed.
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
    // lists of unsubscribable vs. not unsubscribable person links.
    var all_subscribers = Y.all('#subscribers-links div');
    if (all_subscribers.size() > 0) {
        all_subscribers.each(function(sub_link) {
            if (sub_link.getAttribute('id') !== 'temp-username') {
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
            if (unsubscribables[i] === full_name) {
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
            if (not_unsubscribables[i] === full_name) {
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
    if (host_start !== -1) {
        var host_end = user_uri.indexOf('/', host_start+2);
        return user_uri.substring(host_end, user_uri.length);
    }

    return user_uri;
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

    var error_handler = new Y.lp.client.ErrorHandler();
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
    var error_handler = new Y.lp.client.ErrorHandler();
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
                            var i;
                            for (i=0; i<result.entries.length; i++) {
                                if (result.entries[i].get('member_link') ===
                                    Y.lp.client.get_absolute_uri(
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
    lp_client.get(Y.lp.client.get_absolute_uri(
        subscription.get('person').get('escaped_uri')), config);
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
    subscription.get('person').set_display_name(function () {
        _add_temp_user_name(subscription);
    });
}

function _add_temp_user_name(subscription) {
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
        // Handle the case of no subscribers.
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

}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "json-parse", "substitute", "widget-position-ext",
                        "lazr.formoverlay", "lazr.anim", "lazr.base",
                        "lazr.overlay", "lazr.choiceedit", "lp.app.picker",
                        "lp.client",
                        "lp.client.plugins", "lp.bugs.subscriber",
                        "lp.bugs.subscribers_list",
                        "lp.bugs.bug_notification_level", "lp.app.errors"]});
