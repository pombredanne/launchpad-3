/* Copyright (c) 2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.testing.helpers', function(Y) {

    var ns = Y.namespace('lp.testing.helpers');


    /**
     * Reset the window history state.
     *
     * Useful for tearDown for code that modifies and stores data into the
     * History.state.
     * @function
     */
    ns.reset_history = function () {
        var win = Y.config.win;
        var originalURL = (win && win.location.toString()) || '';
        win.history.replaceState(null, null, originalURL);
    };


    ns.LPClient = function () {
        if (!(this instanceof ns.LPClient)) {
            throw new Error("Constructor called as a function");
        }
        this.received = [];
        // LPClient provides mocks of the lp.client calls
        // Simulates a call to Y.lp.client.named_post
        this.named_post = function(url, func, config) {
            this._call('named_post', config, arguments);
        };
        // Simulates a PATCH call through Y.lp.client
        this.patch = function(bug_filter, data, config) {
            this._call('patch', config, arguments);
        };
        // Simulates a GET call through Y.lp.client
        this.get = function(url, config) {
            this._call('get', config, arguments);
        };
    }
    ns.LPClient.prototype._call = function(name, config, args) {
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

}, '0.1', {
    'requires': [ 'history']
});
