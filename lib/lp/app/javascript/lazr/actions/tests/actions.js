/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI().use('lazr.actions', 'lazr.testing.runner', 'node',
          'event', 'event-simulate', 'console', function(Y) {

var Assert = Y.Assert;  // For easy access to isTrue(), etc.

var suite = new Y.Test.Suite("Actions Tests");

var permissions = {};

var permission_factory = function(perm) {
    var perm_check = function() {
        return permissions[perm];
    };
    return perm_check;
};

suite.add(new Y.Test.Case({

    name: 'actions_basics',

    setUp: function() {
        this.workspace = Y.one('#workspace');
        if (!this.workspace){
            Y.one(document.body).append(Y.Node.create(
                '<div id="workspace">'
                + '<div id="monkeys"></div>'
                + '<div id="monkeys-container"></div>'
                + '</div>'));
            this.workspace = Y.one('#workspace');
        }
        this.actions_helper = new Y.lazr.actions.ActionsHelper(
            {
                actions: [
                    new Y.lazr.actions.Action(
                        {title: "See No Evil",
                         action: function() { Y.log('Saw some evil.'); },
                         permission: permission_factory('can_see')}),
                    new Y.lazr.actions.Action(
                        {title: "Hear No Evil",
                         action: function() { Y.log('Heard some evil.'); },
                         permission: permission_factory('can_hear')}),
                    new Y.lazr.actions.Action(
                        {title: "Speak No Evil",
                         action: function() { Y.log('Spoke some evil.'); }})
                    ],
                actionsId: "monkeys-container"
            });
    },

    tearDown: function() {
        this.workspace.remove();
    },

    test_can_see_and_hear_and_talk: function() {
        permissions.can_see = true;
        permissions.can_hear = true;
        permissions.can_speak = false; // won't matter, action isn't bound to permission

        var container = Y.one("#monkeys");
        this.actions_helper.render(container);

        Assert.isTrue(container.all('li').size() == 3, 'Woops, wrong number of children')
    },

    test_can_see_and_talk: function() {
        permissions.can_see = true;
        permissions.can_hear = false;
        permissions.can_speak = false; // won't matter, action isn't bound to permission

        var container = Y.one("#monkeys");
        this.actions_helper.render(container);

        var second_action = this.actions_helper.get('actions')[1];
        var second_item = second_action.get('item');

        // the actions helper still renders
        Assert.isTrue(container.all('li').size() == 3, 'Woops, wrong number of children');
        // but the second item is now disabled, via CSS
        Assert.isTrue(second_item.hasClass('lazr-action-disabled'), "Didn't get disabled properly");
    }
}));

Y.lazr.testing.Runner.add(suite);
Y.lazr.testing.Runner.run();
});
