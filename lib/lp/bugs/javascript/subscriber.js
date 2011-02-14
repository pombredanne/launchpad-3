/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Objects for subscription handling.
 *
 * @module bugs
 * @submodule subscriber
 */

YUI.add('lp.bugs.subscriber', function(Y) {

var namespace = Y.namespace('lp.bugs.subscriber');
namespace.subscription_labels = {
    'EDIT': 'Edit subscription',
    'SUBSCRIBE': 'Subscribe',
    'UNSUBSCRIBE': 'Unsubscribe'
};


/**
 * A Subscription object which represents the subscription
 * being attempted.
 *
 * @class Subscription
 * @namespace lp
 */
function Subscription(config) {
    Subscription.superclass.constructor.apply(this, arguments);
}

Subscription.ATTRS = {
    'link': {
        value: null
    },

    'can_be_unsubscribed': {
        value: false
    },

    'is_direct': {
        value: true
    },

    'has_dupes': {
        value: false
    },

    'person': {
        value: null
    },

    'is_team': {
        value: false
    },

    'subscriber': {
        value: null
    },

    'spinner': {
        vallue: null
    },

    'bug_notification_level': {
        value: 'Discussion'
    }
};

Y.extend(Subscription, Y.Base, {

    /**
     * Is the current subscription link a node?
     * Useful in checking that the link is defined.
     *
     * @method is_node
     * @return {Boolean}
     */
    'is_node': function() {
        return this.get('link') instanceof Y.Node;
    },

    /**
     * Is the person being subscribed already subscribed?
     *
     * @method is_already_subscribed
     * @return {Boolean}
     */
    'is_already_subscribed': function() {
        var display_name = this.get('person').get('full_display_name');
        var already_subscribed = false;

        Y.all('#subscribers-links div').each(function(link) {
            var name = link.one('a').getAttribute('name');
            if (name == display_name) {
                already_subscribed = true;
            }
        });

        return already_subscribed;
    },

    /**
     * Can this subscriber being unsubscribed by the current
     * user?
     *
     * @method can_be_unsubscribed_by_user
     * @return {Boolean}
     */
    'can_be_unsubscribed_by_user': function() {
        return this.get('can_be_unsubscribed');
    },

    /**
     * Is this the current user subscribing him/herself?
     *
     * @method is_current_user_subscribing
     * @return {Boolean}
     */
    'is_current_user_subscribing': function() {
        return (
            this.get('subscriber').get('name') ==
            this.get('person').get('name')
        );
    },

    /**
     * Is the current subscription a direct subscription?
     *
     * @method is_direct_subscription
     * @return {Boolean}
     */
    'is_direct_subscription': function() {
        return this.get('is_direct');
    },

    /**
     * Does this subscription have dupes?
     *
     * @method has_duplicate_subscriptions
     * @return {Boolean}
     */
    'has_duplicate_subscriptions': function() {
        return this.get('has_dupes');
    },

    /**
     * Is this subscriber a team?
     *
     * @method is_team
     * @return {Boolean}
     */
    'is_team': function() {
        return this.get('is_team');
    },

    /**
     * Turn on the progess spinner.
     *
     * @method enable_spinner
     */
    'enable_spinner': function(text) {
        if (Y.Lang.isValue(text)) {
            this.get('spinner').set('innerHTML', text);
        }
        this.get('link').setStyle('display', 'none');
        this.get('spinner').setStyle('display', 'block');
    },

    /**
     * Turn off the progress spinner.
     *
     * @method disable_spinner
     */
    'disable_spinner': function(text) {
        if (Y.Lang.isValue(text)) {
            var link = this.get('link');
            link.set('innerHTML', text);
            if (text == namespace.subscription_labels.SUBSCRIBE) {
                link.removeClass('modify remove');
                link.removeClass('modify edit');
                link.addClass('add');
            } else if (text == namespace.subscription_labels.EDIT) {
                link.removeClass('add');
                link.addClass('modify edit');
            } else {
                link.removeClass('add');
                link.addClass('modify remove');
            }
        }
        this.get('spinner').setStyle('display', 'none');
        this.get('link').setStyle('display', 'inline');
    }
});

namespace.Subscription = Subscription;

/** A Subscriber object which can represent the subscribing person or
 * the person being subscribed.
 *
 * @class Subscriber
 * @namespace lp
 */
function Subscriber(config) {
    Subscriber.superclass.constructor.apply(this, arguments);
}

Subscriber.NAME = 'Subscriber';
Subscriber.ATTRS = {
    uri: {
        value: ''
    },

    name: {
        value: ''
    },

    css_name: {
        value: ''
    },

    escaped_uri: {
        value: ''
    },

    user_node: {
        value: null
    },

    display_name: {
        value: ''
    },

    full_display_name: {
        value: ''
    },

    subscriber_ids: {
        value: null
    }
};

Y.extend(Subscriber, Y.Base, {

    /**
     * Subscriber can take as little as a Person uri and work
     * out most of the person's name attributes from that.
     *
     * The display_name is the tricky part and has to be worked
     * out either from the DOM or via the LP API.  The object can
     * be passed a DOM node in the config, but the object tries
     * to work out the DOM on the fly if not and falls back to
     * the API if LP is available. (See the included display_name
     * methods for more.)
     *
     * @method initializer
     */
    initializer: function(config) {
        if (this.get('uri') !== '') {
            this.set('name', this.get('uri').substring(2));
            var name = this.get('name');

            // If we have a subscriber_ids object and that object
            // has an entry for this Subscriber, then set css_name.
            // Otherwise, create a css_name with a guid and update
            // subscriber_ids to include it.
            var subscriber_ids = this.get('subscriber_ids');
            if (Y.Lang.isValue(subscriber_ids)) {
                var css_name = this.get('subscriber_ids')[name];
                if (Y.Lang.isValue(css_name)) {
                    this.set('css_name', css_name);
                } else {
                    css_name = 'subscriber-' + Y.guid();
                    subscriber_ids[name] = css_name;
                    this.set('subscriber_ids', subscriber_ids);
                    this.set('css_name', css_name);
                }
            }

            // Handle the case of plus signs in user names.
            var escaped_uri;
            if (name.indexOf('+') > 0) {
                escaped_uri = name.replace('+', '%2B');
            } else {
                escaped_uri = name;
            }
            this.set('escaped_uri', '/~' + escaped_uri);
        }

        this.set_display_name();
        this.set_truncated_display_name();
    },

    /**
     * Finds the display name using the LP API.
     *
     * @method get_display_name_from_api
     * @param client {Object} An LP API client.
     */
    get_display_name_from_api: function(client) {
        var self = this;
        var cfg = {
            on: {
                success: function(person) {
                    self.set(
                        'display_name', person.lookup_value('display_name'));
                    self.set_truncated_display_name();
                    self.fire('displaynameload');
                }
            }
        };
        client.get(this.get('escaped_uri'), cfg);
    },

    /** Finds the display name in a DOM node.
     *
     * This method can use a DOM node supplied in the config but
     * will also try the standard class name for a subscriber's
     * node.
     *
     * @method get_display_name_from_node
     */
    get_display_name_from_node: function() {
        var user_node;
        if (Y.Lang.isValue(this.get('user_node'))) {
            user_node = this.get('user_node');
        } else {
            user_node = Y.one('.subscriber-' + this.get('name'));
        }

        if (Y.Lang.isValue(user_node)) {
            this.set('user_node', user_node);
            var anchor = this.get('user_node').one('a');
            var display_name = anchor.get('name');
            return display_name;
        } else {
            return '';
        }
    },

    /**
     * A wrapper around the other getDisplayNameXXX functions to
     * work out if setting the display_name is possible.  Calling
     * this is the safest way to ensure display_name is set
     * correctly.
     *
     * @method set_display_name
     */
    set_display_name: function() {
        var display_name = this.get_display_name_from_node();
        if (display_name !== '') {
            this.set('display_name', display_name);
            this.set_truncated_display_name();
            this.fire('displaynameload');
        } else {
            if (window.LP !== undefined &&
                window.LP.client.links.me !== undefined) {
                var client = new LP.client.Launchpad();
                this.get_display_name_from_api(client);
            }
        }
    },

    /**
     * Sets the truncated version of the display_name.
     *
     * @method set_truncated_display_name
     */
    set_truncated_display_name: function() {
        var display_name = this.get('display_name');
        if (display_name !== '') {
            var truncated_name;
            if (display_name.length > 20) {
                truncated_name = display_name.substring(0, 17) + '...';
            } else {
                truncated_name = display_name;
            }
            this.set('display_name', truncated_name);
            this.set('full_display_name', display_name);
        }
    }

});

namespace.Subscriber = Subscriber;

}, "0.1", {"requires": ["base", "node"]});
