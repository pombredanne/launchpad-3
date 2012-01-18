/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */
YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
}).use('event', 'lp.client', 'node', 'test', 'widget-stack',
             'console', 'lp.registry.team.mailinglists', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;
var team_mailinglists = Y.lp.registry.team.mailinglists;
var suite = new Y.Test.Suite("team.mailinglists Tests");

suite.add(new Y.Test.Case({

    name: 'setup',

    setUp: function() {
        window.LP = {
            links: {},
            cache: {}
        };
        LP.cache['mail_messages'] = [
            {
                'message_id': 3,
                'headers': {
                    'Subject': 'Please stop breaking things',
                    'To': 'the_list@example.hu',
                    'From': 'someone@else.com',
                    'Date': '2011-10-13',
                },
                'nested_messages': [],
                'attachments': []
            }
        ];
    },

    tearDown: function() {
    },

    test_render_message: function () {
        var message_list = new Y.lp.registry.team.mailinglists.MessageList();          
        var messages = LP.cache['mail_messages'];
        message_list.set('messages', messages);
        message_list.display_messages();
        var message = Y.one("#message-3");
        var subject = message.one();
        Assert.areEqual(message.get('text'), 'Please stop breaking things');
    }
}));


var handle_complete = function(data) {
    window.status = '::::' + JSON.stringify(data);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var yconsole = new Y.Console({
    newestOnTop: false
});
yconsole.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});

});
