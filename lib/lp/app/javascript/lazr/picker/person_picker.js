/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.lazr.person-picker
 * @requires lazr.picker
 */
YUI.add('lazr.person-picker', function(Y) {

/*
 * Extend the picker into the PersonPicker
 */
var footer_label = ".yui3-picker-footer-slot";

var PersonPicker = function() {
    PersonPicker.superclass.constructor.apply(this, arguments);
    this._extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
    Y.after(this._renderPersonPickerUI, this, 'renderUI');
};

Y.extend(PersonPicker, Y.lazr.picker.Picker, {
    initializer: function(cfg) {
        PersonPicker.superclass.initializer.apply(this, arguments);

        var show_assign_me_button = true;
        var show_remove_button = true;
        var assign_button_text = 'Pick Me';
        var remove_button_text = 'Remove Person';

        if (cfg !== undefined) {
            if (cfg.show_assign_me_button !== undefined) {
                show_assign_me_button = cfg.show_assign_me_button;
            }
            if (cfg.show_remove_button !== undefined) {
                show_remove_button = cfg.show_remove_button;
            }
            if (cfg.assign_button_text !== undefined) {
                assign_button_text = cfg.assign_button_text;
            }
            if (cfg.remove_button_text !== undefined) {
                remove_button_text = cfg.remove_button_text;
            }
        }
        this._show_assign_me_button = show_assign_me_button;
        this._show_remove_button = show_remove_button;
        this._assign_me_button_text = assign_button_text;
        this._remove_button_text = remove_button_text;
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        this.constructor.superclass.hide.call(this);
    },

    show: function() {
        this.get('boundingBox').setStyle('display', 'block');
        this.constructor.superclass.show.call(this);
    },

    remove: function () {
        this.fire('save', {value: ''});
    },

    assign_me: function () {
        var name = LP.links.me.replace('/~', '');
        this.fire('save', {value: name});
    },

    _renderPersonPickerUI: function() {
        var remove_button, assign_me_button;

        if (this._show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: ' +
                '1em">' + this._remove_button_text + '</a>');
            remove_button.on('click', this.remove, this);
            this._extra_buttons.appendChild(remove_button);
            this.remove_button = remove_button;
        }

        if (this._show_assign_me_button) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                this._assign_me_button_text + '</a>');
            assign_me_button.on('click', this.assign_me, this);
            this._extra_buttons.appendChild(assign_me_button);
            this.assign_me_button = assign_me_button;
        }
    },

    syncUI: function() {
        // call Picker's sync
        this.constructor.superclass.syncUI.apply(this, arguments);
        footer_slot = Y.one(footer_label);
        footer_slot.appendChild(this._extra_buttons);
    },

    bindUI: function() {
        this.constructor.superclass.bindUI.apply(this, arguments);
        this.after('resultsChange', function(e) {
            var results = this.get('results');
            if (this._search_input.get('value') && !results.length) {
                this._extra_buttons.removeClass('unseen');
            } else {
                this._extra_buttons.addClass('unseen');
            }
        });
    }
});
PersonPicker.NAME = 'picker';
var namespace = Y.namespace('lazr.picker');
namespace.PersonPicker = PersonPicker;

}, "0.1", {"requires": ["lazr.picker"]});
