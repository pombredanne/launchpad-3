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


}, '0.1', {
    'requires': [ 'history']
});
