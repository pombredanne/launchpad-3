/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.lp.registry.personpicker
 * @requires lazr.picker
 */
YUI.add('lp.registry.personpicker', function(Y) {
var namespace = Y.namespace('lp.registry.personpicker');

var footer_label = ".yui3-picker-footer-slot"

var PersonPicker = function() {
    PersonPicker.superclass.constructor.apply(this, arguments);

    this._extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
};

Y.extend(PersonPicker, Y.lazr.Picker, {
    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
    },

    show: function() {
        this.get('boundingBox').setStyle('display', 'block');
    },

    remove: function () {
        this.fire('save', {value: ''});
    },

    assign_me: function () {
        name = LP.links.me.replace('/~', '');
        this.fire('save', {value: name});
    },

    renderUI: function() {
        this.constructor.superclass.renderUI.call(this);
        var remove_button, assign_me_button;
        //# TODO config should set extrabuttons
        var show_remove_button = true;
        var show_assign_me_button = true;
        var remove_button_text = "Remove assignee";
        var assign_me_button_text = "Assign me";
        if (show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: 1em">' +
                remove_button_text + '</a>');
            remove_button.on('click', this.remove, this);
            this._extra_buttons.appendChild(remove_button);
        }
        if (show_assign_me_button) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                assign_me_button_text + '</a>');
            assign_me_button.on('click', this.assign_me, this);
            this._extra_buttons.appendChild(assign_me_button);
        }
    },

    syncUI: function() {
        // call Picker's sync
        this.constructor.superclass.syncUI.call(this);
        footer_slot = Y.one(footer_label);
        footer_slot.appendChild(this._extra_buttons);
    }
});
PersonPicker.NAME = 'person-picker';
namespace.PersonPicker = PersonPicker

}, "0.1", {"requires": ['lazr.picker']});
