/* Copyright (c) 2012, Canonical Ltd. All rights reserved.
 *
 * Team mailinglists
 *
 * @module lp.registry.team.mailinglists
 */

YUI.add('lp.registry.team.mailinglists', function(Y) {

var module = Y.namespace('lp.registry.team.mailinglists');

function MessageList(config) {
    MessageList.superclass.constructor.apply(this, arguments);
}

MessageList.NAME = "messageList";

MessageList.ATTR = {
    forwards_nagivation: {
        value: null
    },

    backwards_navigation: {
        value: null
    },

    messages: {
        value: []
    },

    container: {
        value: null
    }
};

Y.extend(MessageList, Y.Base, {

    initializer: function (config) {
        this.set('container', config.container);
        if (config.messages !== undefined) {
            this.set('messages', config.messages);
        }
        if (config.forwards_navigation !== undefined) {
            this.set('forwards_navigation', config.forwards_navigation);
        }

        if (config.backwards_navigation !== undefined) {
            this.set('backwards_navigation', config.backwards_navigation);
        }

        this._bind_nav();
    },

    _bind_nav: function () {
        /* XXX j.c.sackett 1-2-2012
         * These signals aren't currently caught by anything in the message
         * list. They exist so that once we have batching calls from grackle
         * ironed out we can easily add the functions in wherever they make
         * the most sense, be that here or in a grackle js module.
         *
         * When we are actually integrating grackle, these may need updating,
         * and we'll need tests ensuring the signals actually *do* something.
         */
        var forwards = this.get('forwards_navigation');
        var backwards = this.get('backwards_navigation');

        forwards.all('.next').on('click', function() {
            this.fire('messageList:next'); 
        })

        forwards.all('.last').on('click', function() {
            this.fire('messageList:last'); 
        })

        backwards.all('.previous').on('click', function() {
            this.fire('messageList:previous'); 
        })

        backwards.all('.first').on('click', function() {
            this.fire('messageList:first'); 
        })
    },

    display_messages: function () {
        var messages = this.get('messages');
        var container = Y.one('#messagelist');
        var i;
        for (i = 0; i < messages.length; i++) {
            var message_node = this._create_message_node(messages[i], 0);
            container.appendChild(message_node);
        }
    },

    _create_message_node: function(message, indent) {
        var message_node = Y.Node.create('<li></li>');
        var message_id = Y.DataType.Number.format(
            message.message_id, {'prefix': 'message-'});
        var subject_node = Y.Node.create('<a href="#"></a>')
            .set('id', message_id)
            .set('text', message.headers.Subject);

        var info = message.headers.From + ', ' + message.headers.Date;
        var info_node = Y.Node.create('<div></div>')
            .set('text', info);
        message_node.appendChild(subject_node);
        message_node.appendChild(info_node);

        if (message.nested_messages !== undefined) {
            indent = indent + 10;
            var nested_messages = Y.Node.create('<ul></ul>');
            var indentation = Y.DataType.Number.format(
                indent, {'suffix': 'px'});
            var i;
            nested_messages.setStyle('margin-left', indentation);

            for (i = 0; i < message.nested_messages.length; i++) {
                nested_node = _create_message_node(
                    message.nested_messages[num], indent);
                nested_messages.appendChild(nested_node);
            }
            message_node.appendChild(nested_messages);
        }
        return message_node;
    }
});
module.MessageList = MessageList;


}, '0.1', {requires: ['base', 'node', 'datatype']});
