/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * The Launchpad Longpoll module provides the functionnality to deal
 * with longpolling on the JavaScript side.
 *
 * @module longpoll
 * @requires event, LP
 */
YUI.add('lp.app.longpoll', function(Y) {

var namespace = Y.namespace('lp.app.longpoll');

namespace.longpoll_start_event = 'lp.app.longpoll.start';
namespace.longpoll_fail_event = 'lp.app.longpoll.failure';

namespace._manager = null;

// After MAX_FAILED_ATTEMPTS failed connections (real failed
// connections  or connection with invalid returns) separate
// by SHORT_DELAY (millisec), wait LONG_DELAY (millisec) before
// trying again to connect.
namespace.MAX_FAILED_ATTEMPTS = 5;
namespace.SHORT_DELAY = 1000;
namespace.LONG_DELAY = 3*60*1000;

function LongPollManager() {
    this.started = false;
    this._failed_attempts = 0;
    this._repoll = true; // Used in tests.
}

/**
 *
 * A Long Poll Manager creates and manages a long polling connexion
 * to the server to fetch events. This class is not directly used
 * but manager through 'setupLongPollManager' which creates and
 * initialises a singleton LongPollManager.
 *
 * @class LongPollManager
 */
namespace.LongPollManager = LongPollManager;

LongPollManager.prototype.initialize = function(queue_name, uri) {
    this._sequence = 0;
    this.queue_name = queue_name;
    this.uri = uri;
};

LongPollManager.prototype.io = function (uri, config) {
    Y.io(uri, config);
};

LongPollManager.prototype.success_poll = function (id, response) {
    try {
        var data = Y.JSON.parse(response.responseText);
        var event_key = data.event_key;
        var event_data = data.event_data;
        Y.fire(event_key, event_data);
        return true;
    }
    catch (e) {
        Y.fire(namespace.longpoll_fail_event, e);
        return false;
    }
};

LongPollManager.prototype.failure_poll = function () {
    Y.fire(namespace.longpoll_fail_event);
};

LongPollManager.prototype._poll_delay = function() {
    this._failed_attempts = this._failed_attempts + 1;
    if (this._failed_attempts >= namespace.MAX_FAILED_ATTEMPTS) {
        this._failed_attempts = 0;
        return namespace.LONG_DELAY;
    }
    else {
        return namespace.SHORT_DELAY;
    }
};

/**
 * Relaunch a connection to the server after a successful or
 * a failed connection.
 *
 * @method repoll
 * @param {Boolean} failed: whether or not the previous connection
 *     has failed.
 */
LongPollManager.prototype.repoll = function(failed) {
    if (!failed) {
        this._failed_attempts = 0;
        if (this._repoll) {
            this.poll();
        }
    }
    else {
        var delay = this._poll_delay();
        if (this._repoll) {
            Y.later(delay, this, this.poll);
        }
    }
};

LongPollManager.prototype.poll = function() {
    var closure = this;
    var config = {
        method: "GET",
        sync: false,
        on: {
            failure: function() {
                closure.failure_poll();
                closure.repoll(true);
            },
            success: function(id, response) {
                var res = closure.success_poll(id, response);
                closure.repoll(res);
            }
        }
    };
    this._sequence = this._sequence + 1;
    var queue_uri = this.uri +
        "?uuid=" + this.queue_name +
        "&sequence=" + this._sequence;
    if (!this.started) {
        Y.fire(namespace.longpoll_start_event);
        this.started = true;
    }
    this.io(queue_uri, config);
};

namespace.getLongPollManager = function() {
    if (!Y.Lang.isValue(namespace._manager)) {
        namespace._manager = new namespace.LongPollManager();
    }
    return namespace._manager;
};

namespace.setupLongPollManager = function() {
    if (Y.Lang.isValue(LP.cache.longpoll)) {
        var queue_name = LP.cache.longpoll.key;
        var uri = LP.cache.longpoll.uri;
        var longpollmanager = namespace.getLongPollManager();
        longpollmanager.initialize(queue_name, uri);
        longpollmanager.poll();
        return longpollmanager;
    }
};

}, "0.1", {"requires":["event", "plugin", "lang", "json", "io"]});
