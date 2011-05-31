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
};

Y.extend(PersonPicker, Y.lazr.Picker, {
    bindUI: function() {
        //call Picker's bindUI
        this.constructor.superclass.bindUI.call(this);
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
    },

    show: function() {
        this.get('boundingBox').setStyle('display', 'block');
    },

    renderUI: function() {
        var extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
        var remove_button, assign_me_button;
        //# TODO config should set extrabuttons
        var show_remove_button = true;
        var show_assign_me_button = true;
        var remove_button_text = "Remove me";
        var assign_me_button_text = "Assign me";
        if (show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: 1em">' +
                remove_button_text + '</a>');
            remove_button.on('click', this.remove);
            extra_buttons.appendChild(remove_button);
        }
        if (show_assign_me_button) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                assign_me_button_text + '</a>');
            assign_me_button.on('click', this.assign_me);
            extra_buttons.appendChild(assign_me_button);
        }
        this.extra_buttons = extra_buttons;
    },

    syncUI: function() {
        // call Picker's render
        this.constructor.superclass.syncUI.call(this);
        footer_slot = Y.one(footer_label);    
        footer_slot.appendChild(this.extra_buttons);
    },
        
    // TODO: Need actual functions
    remove: function () {},
    assign_me: function () {}
});
PersonPicker.NAME = 'person-picker';
namespace.PersonPicker = PersonPicker

}, "0.1", {"requires": ['lazr.picker']});
