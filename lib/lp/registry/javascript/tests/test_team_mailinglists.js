/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */
YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw',
    combine: false,
    fetchCSS: false
}).use('event', 'lp.mustache', 'node', 'test', 'widget-stack',
             'console', 'lp.registry.team.mailinglists', function(Y) {

// Local aliases
var Assert = Y.Assert,
    ArrayAssert = Y.ArrayAssert;
var team_mailinglists = Y.lp.registry.team.mailinglists;
var suite = new Y.Test.Suite("team.mailinglists Tests");

suite.add(new Y.Test.Case({

    name: 'Team Mailinglists',

    setUp: function() {
        window.LP = {
            links: {},
            cache: {}
        };
    },

    tearDown: function() {
    },

    test_render_message: function () {
        var config = {
            messages: [
                {
                    'message_id': 3,
                    'headers': {
                        'Subject': 'Please stop breaking things',
                        'To': 'the_list@example.hu',
                        'From': 'someone@else.com',
                        'Date': '2011-10-13'
                    },
                    'nested_messages': [],
                    'attachments': []
                }
            ],
            container: Y.one('#messagelist'),
            forwards_navigation: Y.all('.last,.next'),
            backwards_navigation: Y.all('.first,.previous')
        };
        var message_list = new Y.lp.registry.team.mailinglists.MessageList(
            config);
        message_list.display_messages();
        var message = Y.one("#message-3");
        console.log(message);
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
