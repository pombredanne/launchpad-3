YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.bugtask_index.portlets.subscription',
           'node-event-simulate', function(Y) {

var suite = new Y.Test.Suite(
    "lp.bugs.bugtask_index.portlets.subscription Tests");
var module = Y.lp.bugs.bugtask_index.portlets.subscription;

/**
 * XXX gary 2011-05-26 bug XXX
 * LPClient is copied three times (see also test_structural_subscription.js
 * and test_subscription.js).  It should be pushed to a shared test module.  
 */
function LPClient(){
    if (!(this instanceof LPClient)) {
        throw new Error("Constructor called as a function");
    }
    this.received = [];
    // We create new functions every time because we allow them to be
    // configured.
    this.named_post = function(url, func, config) {
        this._call('named_post', config, arguments);
    };
    this.patch = function(bug_filter, data, config) {
        this._call('patch', config, arguments);
    };
}
LPClient.prototype._call = function(name, config, args) {
    this.received.push(
        [name, Array.prototype.slice.call(args)]);
    if (!Y.Lang.isValue(args.callee.args)) {
        throw new Error("Set call_args on "+name);
    }
    var do_action = function () {
        if (Y.Lang.isValue(args.callee.fail) && args.callee.fail) {
            config.on.failure.apply(undefined, args.callee.args);
        } else {
            config.on.success.apply(undefined, args.callee.args);
        }
    };
    if (Y.Lang.isValue(args.callee.halt) && args.callee.halt) {
        args.callee.resume = do_action;
    } else {
        do_action();
    }
};

function make_status_node() {
    var status = Y.Node.create('<div/>')
        .set('id', 'current_user_subscription')
        .append(Y.Node.create('<span/>'));
    Y.one('body').appendChild(status);
    return status;
}

function add_link_to_status_node() {
    var status = Y.one('#current_user_subscription');
    status.append(
        Y.Node.create('<a/>')
            .addClass('menu-link-subscription')
            .addClass('sprite')
            .addClass('modify')
            .addClass('edit')
            .set('href', 'http://example.com')
            .set('text', 'Example text')
        );
}

function make_mute_node() {
    var parent = Y.Node.create('<div/>')
        .set('id', 'mute-link-container')
        .append(Y.Node.create('<a/>')
            .addClass('menu-link-mute_subscription')
            .addClass(module.UNMUTED_CLASS)
            .set('text', 'This is a mute link')
            .set('href', 'http://www.example.com/+mute')
        );
    Y.one('body').appendChild(parent);
    return parent;
}

function set_LP_cache(bug_link) {
    window.LP = {cache: {
        notifications_text: {
            not_only_other_subscription: 'You are',
            only_other_subscription: 
                'You have subscriptions that may cause you to receive ' +
                'notifications, but you are',
            direct_all: 'subscribed to all notifications for this bug.',
            direct_metadata: 
                'subscribed to all notifications except comments for ' +
                'this bug.',
            direct_lifecycle: 
                'subscribed to notifications when this bug is closed ' +
                'or reopened.',
            not_direct: 
                "not directly subscribed to this bug's notifications.",
            muted: 
                'Your personal email notifications from this bug are muted.'
            },
        context: {web_link: 'http://example.com', bug_link: bug_link},
        other_subscription_notifications: false
        }};
}

// Notification levels.
var COMMENTS = 'Discussion';
var METADATA = 'Details';
var LIFECYCLE = 'Lifecycle';

function make_subscription(level) {
    if (Y.Lang.isUndefined(level)) {
        level = COMMENTS;
    }
    window.LP.cache.subscription = {'bug_notification_level': level};
}

/**
 * Test update_subscription_status.
 */
suite.add(new Y.Test.Case({
    name: 'Test update_subscription_status',

    setUp: function() {
        this.status_node = make_status_node();
        this.mute_node = make_mute_node();
        add_link_to_status_node();
        set_LP_cache();
    },

    tearDown: function() {
        this.status_node.remove();
        this.mute_node.remove();
        delete window.LP;
    },

    test_can_create_link: function() {
        this.status_node.one('a').remove();
        make_subscription();
        Y.Assert.isTrue(Y.Lang.isNull(this.status_node.one('a')));
        module.update_subscription_status()
        var link = this.status_node.one('a');
        Y.Assert.isTrue(Y.Lang.isValue(link));
        Y.Assert.isTrue(link.hasClass('menu-link-subscription'));
        Y.Assert.isTrue(link.hasClass('sprite'));
        Y.Assert.isTrue(link.hasClass('modify'));
        Y.Assert.isTrue(link.hasClass('edit'));
        Y.Assert.isTrue(link.hasClass('js-action'));
        Y.Assert.areEqual(
            // window.LP.context.web_link + '/+subscribe',
            'http://example.com/+subscribe',
            link.get('href'));
    },

    test_no_subscription: function() {
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            "not directly subscribed to this bug's notifications.",
            this.status_node.one('a').get('text'));
    },

    test_other_subscription: function() {
        window.LP.cache.other_subscription_notifications = true;
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You have subscriptions that may cause you to receive ' +
            'notifications, but you are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            "not directly subscribed to this bug's notifications.",
            this.status_node.one('a').get('text'));
    },

    test_full_subscription: function() {
        make_subscription(COMMENTS);
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            "subscribed to all notifications for this bug.",
            this.status_node.one('a').get('text'));
    },

    test_metadata_subscription: function() {
        make_subscription(METADATA);
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            'subscribed to all notifications except comments for this bug.',
            this.status_node.one('a').get('text'));
    },

    test_lifecycle_subscription: function() {
        make_subscription(LIFECYCLE);
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            'subscribed to notifications when this bug is closed or ' +
            'reopened.',
            this.status_node.one('a').get('text'));
    },

    test_direct_subscription_has_precedence: function() {
        window.LP.cache.other_subscription_notifications = true;
        make_subscription(LIFECYCLE);
        module.update_subscription_status()
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            'subscribed to notifications when this bug is closed or ' +
            'reopened.',
            this.status_node.one('a').get('text'));
    },

    test_muted_subscription: function() {
        make_subscription(LIFECYCLE);
        this.mute_node.one('a').replaceClass(
            module.UNMUTED_CLASS, module.MUTED_CLASS);
        Y.Assert.isTrue(Y.Lang.isValue(this.status_node.one('a')));
        module.update_subscription_status()
        Y.Assert.areEqual(
            'Your personal email notifications from this bug are muted.',
            this.status_node.one('span').get('text'));
        Y.Assert.isFalse(Y.Lang.isValue(this.status_node.one('a')));
    }

}));

/**
 * Test setup_mute_link_handlers.
 */
suite.add(new Y.Test.Case({
    name: 'Test setup_mute_link_handlers',

    setUp: function() {
        this.status_node = make_status_node();
        this.mute_node = make_mute_node();
        this.link = this.mute_node.one('a');
        add_link_to_status_node();
        this.bug_link = 'http://example.net/firefox/bug/1';
        set_LP_cache(this.bug_link);
        make_subscription(COMMENTS);
        module.update_subscription_status();
        module.setup_mute_link_handlers();
        module._lp_client = new LPClient();
        module._lp_client.named_post.args = [];
    },

    tearDown: function() {
        this.status_node.remove();
        this.mute_node.remove();
        delete window.LP;
        delete module._lp_client;
        var error_overlay = Y.one('.yui3-lazr-formoverlay');
        if (Y.Lang.isValue(error_overlay)) {
            error_overlay.remove();
        }
    },

    test_mute_success: function() {
        this.link.simulate('click');
        Y.Assert.areEqual(1, module._lp_client.received.length);
        Y.Assert.areEqual('named_post', module._lp_client.received[0][0]);
        var args = module._lp_client.received[0][1];
        Y.Assert.areEqual(this.bug_link, args[0]);
        Y.Assert.areEqual('mute', args[1]);
        Y.ObjectAssert.areEqual({}, args[2].parameters);
        Y.Assert.isTrue(this.link.hasClass(module.MUTED_CLASS));
        Y.Assert.isFalse(this.link.hasClass('spinner'));
        Y.Assert.isFalse(this.link.hasClass(module.UNMUTED_CLASS));
        Y.Assert.areEqual(
            'Your personal email notifications from this bug are muted.',
            this.status_node.one('span').get('text'));
    },

    test_unmute_success: function() {
        this.link.replaceClass(module.UNMUTED_CLASS, module.MUTED_CLASS);
        this.link.simulate('click');
        Y.Assert.areEqual(1, module._lp_client.received.length);
        Y.Assert.areEqual('named_post', module._lp_client.received[0][0]);
        var args = module._lp_client.received[0][1];
        Y.Assert.areEqual(this.bug_link, args[0]);
        Y.Assert.areEqual('unmute', args[1]);
        Y.ObjectAssert.areEqual({}, args[2].parameters);
        Y.Assert.isTrue(this.link.hasClass(module.UNMUTED_CLASS));
        Y.Assert.isFalse(this.link.hasClass('spinner'));
        Y.Assert.isFalse(this.link.hasClass(module.MUTED_CLASS));
        Y.Assert.areEqual(
            'You are',
            this.status_node.one('span').get('text'));
        Y.Assert.areEqual(
            "subscribed to all notifications for this bug.",
            this.status_node.one('a').get('text'));
    },

    test_mute_spinner_and_failure: function() {
        module._lp_client.named_post.fail = true;
        module._lp_client.named_post.args = [
            true,
            {status: 400, responseText: 'Rutebegas!'}];
        module._lp_client.named_post.halt = true;
        this.link.simulate('click');
        // Right now, this is as if we are waiting for the server to
        // reply. The link is spinning.
        Y.Assert.isTrue(this.link.hasClass('spinner'));
        Y.Assert.isFalse(this.link.hasClass(module.UNMUTED_CLASS));
        // Now the server replies with an error.
        module._lp_client.named_post.resume();
        // We have no spinner.
        Y.Assert.isTrue(this.link.hasClass(module.UNMUTED_CLASS));
        Y.Assert.isFalse(this.link.hasClass('spinner'));
        // The page has rendered the error overlay.
        var error_box = Y.one('.yui3-lazr-formoverlay-errors');
    }

}));


Y.Test.Runner.on('complete', function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    });
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
