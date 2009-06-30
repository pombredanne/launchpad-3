/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Object for subscriber handling.
 *
 * @module Y.lp.subscriber
 */

YUI.add('lp.subscriber', function(Y) {

Y.namespace('lp');

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

    Subscriber.set_display_name(this);
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
    }
};

Subscriber.get_display_name_api = function(user, client) {
    var cfg = {
        on: {
            success: function(person) {
                user.set('display_name', person.lookup_value('display_name'));
                user.fire('displayname:loaded');
            }
        }
    }
    user.client.get(user.get('escaped_uri'), cfg);
}

Subscriber.get_display_name_node = function(user) {
    var anchor = user.get('user_node').query('a');
    return anchor.get('name');
}

Subscriber.set_display_name = function(user) {
    var display_name;
    if (user.get('user_node') !== null) {
        display_name = Subscriber.get_display_name_node(user);
        user.set('display_name', display_name);
        user.fire('displayname:loaded');
    } else {
        if (typeof(LP) != 'undefined') {
            var client = new LP.client.Launchpad();
            Subscriber.get_display_name_api(user, client);
        }
    }
}

Y.augment(Subscriber, Y.Attribute);
Y.lp.Subscriber = Subscriber;

}, '0.1', {requires: ['attribute', 'node',]});
