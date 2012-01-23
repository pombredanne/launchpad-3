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
    messages: {
        value: [],
    }
};

Y.extend(MessageList, Y.Base, {

    display_messages: function () {
        var messages = this.get('messages');
        var message_list = Y.one('#messagelist');
        for (num in messages) {
            var message_node = this._create_message_node(messages[num], 0);
            message_list.appendChild(message_node); 
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
            nested_messages.setStyle('margin-left', indentation);
            
            for (num in message.nested_messages) {
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
