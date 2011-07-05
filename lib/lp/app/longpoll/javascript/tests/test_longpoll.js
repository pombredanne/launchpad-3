/* Copyright (c) 2011, Canonical Ltd. All rights reserved. */

YUI({
    base: '../../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use(
        'test', 'console', 'node-event-simulate', 'json',
        'lp.app.longpoll',
        function(Y) {

    var Assert = Y.Assert;
    var ArrayAssert = Y.ArrayAssert;

    var suite = new Y.Test.Suite("longpoll Tests");
    var longpoll = Y.lp.app.longpoll;

    var attrgetter = function(name) {
        return function(thing) {
            return thing[name];
        };
    };

    var attrselect = function(name) {
        return function(things) {
            return Y.Array(things).map(attrgetter(name));
        };
    };
    var testLongPollSingleton = {
        name: 'TestLongPollSingleton',
        tearDown: function() {
            // Cleanup the singleton;
            longpoll._manager = null;
        },

        testGetSingletonLongPollManager: function() {
            Assert.isNull(longpoll._manager);
            var manager = longpoll.getLongPollManager();
            Assert.isNotNull(longpoll._manager);
            var manager2 = longpoll.getLongPollManager();
            Assert.areSame(manager, manager2);
        },

        testInitLongPollManagerNoLongPoll: function() {
            // if LP.cache.longpoll.key is undefined: no longpoll manager
            // is created by setupLongPollManager.
            window.LP = {
                links: {},
                cache: {}
            };

            longpoll.setupLongPollManager(true);
            Assert.isNull(longpoll._manager);
        },

        testInitLongPollManagerLongPoll: function() {
            window.LP = {
                links: {},
                cache: {}
            };

            LP.cache.longpoll = {
                key: 'key',
                uri: '/+longpoll/'
            };
            longpoll.setupLongPollManager(true);
            Assert.isNotNull(longpoll._manager);
        }
    };

    suite.add(new Y.Test.Case(testLongPollSingleton));

    var testLongPoll = {
        name: 'TestLongPoll',

        setUp: function() {
            var manager = longpoll.getLongPollManager();
            manager._repoll = false;
            this.createBaseLP();
        },

        tearDown: function() {
            // Cleanup the singleton;
            longpoll._manager = null;
        },

        createBaseLP:function() {
            window.LP = {
                links: {},
                cache: {}
            };
        },

        setupLPCache: function() {
            LP.cache.longpoll = {
                key: 'key',
                uri: '/+longpoll/'
            };
        },

       setupLongPoll: function(nb_calls) {
            this.setupLPCache();
            return longpoll.setupLongPollManager(true);
        },

        testInitLongPollManagerQueueName: function() {
            var manager = this.setupLongPoll();
            Assert.areEqual(LP.cache.longpoll.key, manager.queue_name);
            Assert.areEqual(LP.cache.longpoll.uri, manager.uri);
            Assert.isFalse(Y.Lang.isValue(manager.nb_calls));
        },

        testPollStarted: function() {
            var fired = false;
            Y.on(longpoll.longpoll_start_event, function() {
                fired = true;
            });
            var manager = this.setupLongPoll();
            Assert.isTrue(fired, "Start event not fired.");
        },

        xtestPollFailure: function() {
            var fired = false;
            Y.on(longpoll.longpoll_fail_event, function() {
                fired = true;
            });
            // Monkeypatch io to simulate failure.
            var manager = longpoll.getLongPollManager();
            manager.io = function(uri, config) {
                config.on.failure();
            };
            this.setupLongPoll();
            Assert.isTrue(fired, "Failure event not fired.");
        },

        testSuccessPollInvalidData: function() {
            var manager = longpoll.getLongPollManager();
            var custom_response = "{{";
            var response = {
                responseText: custom_response
            };
            var res = manager.success_poll("2", response);
            Assert.isFalse(res);
        },

        testSuccessPollMalformedData: function() {
            var manager = longpoll.getLongPollManager();
            var response = {
                responseText: '{ "event_data": "6" }'
            };
            var res = manager.success_poll("2", response);
            Assert.isFalse(res);
         },

         testSuccessPollWellformedData: function() {
            var manager = longpoll.getLongPollManager();
            var response = {
                responseText: '{ "event_key": "4", "event_data": "6"}'
            };
            var res = manager.success_poll("2", response);
            Assert.isTrue(res);
        },

        testPollDelay: function() {
            var manager = longpoll.getLongPollManager();
            // Monkeypatch io to simulate failure.
            manager.io = function(uri, config) {
                config.on.failure();
            };
            Assert.areEqual(0, manager._failed_attempts);
            this.setupLongPoll();
            Assert.areEqual(1, manager._failed_attempts);
            var i;
            for (i=0; i<longpoll.MAX_FAILED_ATTEMPTS-1; i++) {
                Assert.areEqual(i+1, manager._failed_attempts);
                manager.poll(); // Fail.
            }
            // _failed_attempts has been reset.
            Assert.areEqual(0, manager._failed_attempts);
        },

        testPollUriSequence: function() {
            // Each new polling increses the sequence parameter:
            // /+longpoll/?uuid=key&sequence=1
            // /+longpoll/?uuid=key&sequence=2
            // /+longpoll/?uuid=key&sequence=3
            // ..
            var count = 0;
            // Monkeypatch io to simulate failure.
            var manager = longpoll.getLongPollManager();
            manager.io = function(uri, config) {
                Assert.areEqual(
                    '/+longpoll/?uuid=key&sequence=' + (count+1),
                    uri);
                count = count + 1;
                var response = {
                   responseText: '{"i":2}'
                };
                config.on.success(2, response);
            };
            this.setupLongPoll();
            Assert.isTrue(count === 1, "Uri not requested.");
        },

        testPollPayLoadBad: function() {
            // If a non valid response is returned, longpoll_fail_event
            // is fired.
            var fired = false;
            Y.on(longpoll.longpoll_fail_event, function() {
                fired = true;
            });
            var manager = longpoll.getLongPollManager();
            // Monkeypatch io.
            manager.io = function(uri, config) {
                var response = {
                   responseText: "{non valid json"
                };
                config.on.success(2, response);
            };
            this.setupLongPoll();
            Assert.isTrue(fired, "Failure event not fired.");
        },

        testPollPayLoadOk: function() {
            // Create a valid message.
            var custom_event = 'my-event';
            var custom_payload = {5: 'i'};
            var custom_response = {
                'event_key': custom_event,
                'event_data': custom_payload
            };
            var fired = false;
            Y.on(custom_event, function(data) {
                fired = true;
                Assert.areEqual(data, custom_payload);
            });
            var manager = longpoll.getLongPollManager();
            // Monkeypatch io.
            manager.io = function(uri, config) {
                var response = {
                   responseText: Y.JSON.stringify(custom_response)
                };
                config.on.success(2, response);
            };
            this.setupLongPoll();
            Assert.isTrue(fired, "Custom event not fired.");
        }


    };

    suite.add(new Y.Test.Case(testLongPoll));

    // Lock, stock, and two smoking barrels.
    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});
