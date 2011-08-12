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
var PersonPicker;

PersonPicker = function() {
    PersonPicker.superclass.constructor.apply(this, arguments);
    this._extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
    Y.after(this._renderPersonPickerUI, this, 'renderUI');
};

Y.extend(PersonPicker, Y.lazr.picker.Picker, {
    initializer: function(cfg) {
        PersonPicker.superclass.initializer.apply(this, arguments);

        var show_assign_me_button = true;
        var show_remove_button = true;
        var assign_me_text = 'Pick me';
        var remove_person_text = 'Remove person';
        var remove_team_text = 'Remove team';
        if (cfg !== undefined) {
            if (cfg.show_assign_me_button !== undefined) {
                show_assign_me_button = cfg.show_assign_me_button;
            }
            if (cfg.show_remove_button !== undefined) {
                show_remove_button = cfg.show_remove_button;
            }
            if (cfg.assign_me_text !== undefined) {
                assign_me_text = cfg.assign_me_text;
            }
            if (cfg.remove_person_text !== undefined) {
                remove_person_text = cfg.remove_person_text;
            }
            if (cfg.remove_team_text !== undefined) {
                remove_team_text = cfg.remove_team_text;
            }
        }
        /* Only show assign-me when the user is logged-in. */
        show_assign_me_button = (
            show_assign_me_button && Y.Lang.isValue(LP.links.me));
        this._show_assign_me_button = show_assign_me_button;
        this._show_remove_button = show_remove_button;
        this._assign_me_text = assign_me_text;
        this._remove_person_text = remove_person_text;
        this._remove_team_text = remove_team_text;
    },

    hide: function() {
        this.get('boundingBox').setStyle('display', 'none');
        this.constructor.superclass.hide.call(this);
    },

    show: function() {
        this.get('boundingBox').setStyle('display', 'block');
        this.constructor.superclass.show.call(this);
    },

    _update_button_text: function() {
        var link_text = this._remove_person_text;
        if (this.get('selected_value_metadata') === 'team') {
            link_text = this._remove_team_text;
        }
        this.remove_button.set('text', link_text);
    },

    _show_hide_buttons: function () {
        var selected_value = this.get('selected_value');
        if (this.remove_button) {
            if (selected_value === null) {
                this.remove_button.addClass('yui3-picker-hidden');
            } else {
                this.remove_button.removeClass('yui3-picker-hidden');
                this._update_button_text();
            }
        }

        if (this.assign_me_button) {
            if (LP.links.me.match('~' + selected_value + "$") ||
                LP.links.me === selected_value) {
                this.assign_me_button.addClass('yui3-picker-hidden');
            } else {
                this.assign_me_button.removeClass('yui3-picker-hidden');
            }
        }
    },

    remove: function () {
        this.hide();
        this.fire(Y.lazr.picker.Picker.SAVE, {value: null});
    },

    assign_me: function () {
        var name = LP.links.me.replace('/~', '');
        this.fire(Y.lazr.picker.Picker.SAVE, {
            image: '/@@/person',
            title: 'Me',
            api_uri: LP.links.me,
            value: name
        });
    },

    _renderPersonPickerUI: function() {
        var remove_button, assign_me_button;

        if (this._show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: ' +
                '1em">' + this._remove_person_text + '</a>');
            remove_button.on('click', this.remove, this);
            this._extra_buttons.appendChild(remove_button);
            this.remove_button = remove_button;
        }

        if (this._show_assign_me_button) {
            assign_me_button = Y.Node.create(
                '<a class="yui-picker-assign-me-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/person)">' +
                this._assign_me_text + '</a>');
            assign_me_button.on('click', this.assign_me, this);
            this._extra_buttons.appendChild(assign_me_button);
            this.assign_me_button = assign_me_button;
        }
        this._search_input.insert(
            this._extra_buttons, this._search_input.get('parentNode'));
        this._show_hide_buttons();
        this.after("selected_valueChange", function(e) {
            this._show_hide_buttons();
        });
    }
});
PersonPicker.NAME = 'picker';
var namespace = Y.namespace('lazr.picker');
namespace.PersonPicker = PersonPicker;

}, "0.1", {"requires": ["lazr.picker"]});
