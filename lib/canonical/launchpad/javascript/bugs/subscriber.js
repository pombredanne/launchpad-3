/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Object for subscriber handling.
 *
 * @module Y.lp.subscriber
 */

YUI.add('lp.subscriber', function(Y) {

Y.namespace('lp');

SubscriptionLink = function() {};

SubscriptionLink.prototype = {
    'isNode': function() {
        return this.get('link') instanceof Y.Node;
    },

    'isAlreadySubscribed': function() {
        var display_name = this.get('person').get('full_display_name');
        var subscribers = Y.get('#subscribers-links');
        var all_subscribers = subscribers.queryAll('div');
        var already_subscribed = false;
        if (Y.Lang.isValue(all_subscribers)) {
            all_subscribers.each(function(link) {
                var name = link.query('a').getAttribute('name');
                if (name == display_name) {
                    already_subscribed = true;
                }
            });
        }
        return already_subscribed;
    },

    'canBeUnsubscribedByUser': function() {
        return this.get('can_be_unsubscribed');
    },

    'isCurrentUserSubscribing': function() {
        return this.get('subscriber') === this.get('person');
    },

    'isDirectSubscription': function() {
        return this.get('is_direct');
    },

    'hasDuplicateSubscriptions': function() {
        return this.get('has_dupes');
    },

    'isTeam': function() {
        return this.get('is_team');
    },

    'enable_spinner': function(text) {
        if (Y.Lang.isValue(text)) {
            this.get('spinner').set('innerHTML', text);
        }
        this.get('link').setStyle('display', 'none');
        this.get('spinner').setStyle('display', 'block');
    },

    'disable_spinner': function(text) {
        if (Y.Lang.isValue(text)) {
            this.get('link').set('innerHTML', text);
            if (text == 'Subscribe') {
                this.get('link').setStyle('background',
                    'url(/@@/add) left center no-repeat');
            } else {
                this.get('link').setStyle('background',
                    'url(/@@/remove) left center no-repeat');
            }
        }
        this.get('spinner').setStyle('display', 'none');
        this.get('link').setStyle('display', 'block');
    }
}

Subscription = function(config) {
    // This is easier in beta1, and Subscriber.ATTRIBUTES
    // is used here to make the upgrade easier.
    //
    // this.addAttrs(Y.merge(Subscriber.ATTRIBUTES), config);
    for (key in Subscription.ATTRIBUTES) {
        if (Y.Lang.isValue(config[key])) {
            this.addAtt(key, {value: config[key]});
        } else {
            this.addAtt(
                key, {value: Subscription.ATTRIBUTES[key].value});
        }
    }
}

Subscription.ATTRIBUTES = {
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
    }
}

Subscription.prototype = new SubscriptionLink();
Y.augment(Subscription, Y.Attribute);

Subscriber = function(config) {
    // This is easier in beta1, and Subscriber.ATTRIBUTES
    // is used here to make the upgrade easier.
    //
    // this.addAttrs(Y.merge(Subscriber.ATTRIBUTES), config);
    for (key in Subscriber.ATTRIBUTES) {
        if (Y.Lang.isValue(config[key])) {
            this.addAtt(key, {value: config[key]});
        } else {
            this.addAtt(
                key, {value: Subscriber.ATTRIBUTES[key].value});
        }
    }

    if (this.get('uri') != '') {
        this.set('name', this.get('uri').substring(2));

        var name = this.get('name');
        var escaped_named = '';
        // Handle the case of plus signs in user names.
        if (name.indexOf('+') > 0) {
            escaped_name = name.replace('+', '%2B');
        } else {
            escaped_name = name;
        }
        this.set('escaped_name', escaped_name);
        this.set('escaped_uri', '/~' + escaped_name);
    }

    if (this.get('display_name') == '') {
        Subscriber.set_display_name(this);
    } else {
        Subscriber.set_truncated_display_name(this);
    }
}

Subscriber.ATTRIBUTES = {
    'uri': {
        value: ''
    },

    'name': {
        value: ''
    },

    'escaped_name': {
        value: ''
    },

    'escaped_uri': {
        value: ''
    },

    'user_node': {
        value: null
    },

    'display_name': {
        value: ''
    },

    'full_display_name': {
        value: ''
    }
};

Subscriber.set_truncated_display_name = function(user) {
    var display_name = user.get('display_name');
    var truncated_name;
    if (display_name.length > 20) {
        truncated_name = display_name.substring(0, 17) + '...';
    } else {
        truncated_name = display_name;
    }
    user.set('display_name', truncated_name);
    user.set('full_display_name', display_name);
}

Subscriber.get_display_name_api = function(user, client) {
    var cfg = {
        on: {
            success: function(person) {
                user.set('display_name', person.lookup_value('display_name'));
                Subscriber.set_truncated_display_name(user);
                user.fire('displayname:loaded');
            }
        }
    }
    client.get(user.get('escaped_uri'), cfg);
}

Subscriber.get_display_name_node = function(user) {
    var user_node;
    if (Y.Lang.isValue(user.get('user_node'))) {
        user_node = user.get('user_node');
    } else {
        user_node = Y.get('.subscriber-' + user.get('name'));
    }

    if (Y.Lang.isValue(user_node)) {
        user.set('user_node', user_node);
        var anchor = user.get('user_node').query('a');
        var display_name = anchor.get('name');
        return display_name
    } else {
        return '';
    }
}

Subscriber.set_display_name = function(user) {
    var display_name = Subscriber.get_display_name_node(user);
    if (display_name !== '') {
        user.set('display_name', display_name);
        Subscriber.set_truncated_display_name(user);
        user.fire('displayname:loaded');
    } else {
        if (typeof(LP) != 'undefined') {
            var client = new LP.client.Launchpad();
            Subscriber.get_display_name_api(user, client);
        }
    }
}

Y.lp.Subscription = Subscription;

Y.augment(Subscriber, Y.Attribute);
Y.lp.Subscriber = Subscriber;

}, '0.1', {requires: ['attribute', 'node',]});
