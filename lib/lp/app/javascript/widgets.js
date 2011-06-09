/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.lp.app.widgets
 * @requires Y.lazr.picker
 */
YUI.add('lp.app.widgets', function(Y) {
var namespace = Y.namespace('lp.app.widgets');

/**
 * Extend the lazr-js Picker.
 */
var Picker = function() {
    Picker.superclass.constructor.apply(this, arguments);
};

Y.extend(Picker, Y.lazr.Picker, {
    // We want to render alt title slightly differently.
    _renderTitleUI: function(data) {
        var li_title = Y.Node.create(
            '<span></span>').addClass(Y.lazr.Picker.C_RESULT_TITLE);
        if (data.title === undefined) {
            // Display an empty element if data is empty.
            return li_title;
        }
        var title = this._text_or_link(
            data.title, data.title_link, data.link_css);
        li_title.appendChild(title);
        if (data.alt_title) {
            var alt_link = null;
            if (data.alt_title_link) {
                alt_link =Y.Node.create('<a></a>')
                    .addClass(data.link_css)
                    .addClass('discreet');
                alt_link.set('text', " Details...")
                    .set('href', data.alt_title_link);
                Y.on('click', function(e) {
                    e.halt();
                    window.open(data.alt_title_link);
                }, alt_link);
            }
            li_title.appendChild('&nbsp;(');
            li_title.appendChild(document.createTextNode(data.alt_title));
            li_title.appendChild(')');
            if (alt_link !== null) {
                li_title.appendChild(alt_link);
            }
        }
        return li_title;
    }
});

Picker.NAME = 'picker';
namespace.Picker = Picker;

/*
 * Extend the picker into the PersonPicker
 */
var footer_label = ".yui3-picker-footer-slot";

var PersonPicker = function() {
    PersonPicker.superclass.constructor.apply(this, arguments);
    this._extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
};

Y.extend(PersonPicker, namespace.Picker, {
    initializer: function(cfg) {
        PersonPicker.superclass.initializer.apply(this, arguments);

        var show_assign_me_button = true;
        var show_remove_button = true;

        if (cfg.show_assign_me_button !== undefined) {
            show_assign_me_button = cfg.show_assign_me_button;
        }
        if (cfg.show_remove_button != undefined) {
            show_remove_button = cfg.show_remove_button;
        }
        this._show_assign_me_button = show_assign_me_button;
        this._show_remove_button = show_remove_button;
    },

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
        var remove_button_text = "Remove assignee";
        var assign_me_button_text = "Assign me";

        if (this._show_remove_button) {
            remove_button = Y.Node.create(
                '<a class="yui-picker-remove-button bg-image" ' +
                'href="javascript:void(0)" ' +
                'style="background-image: url(/@@/remove); padding-right: 1em">' +
                remove_button_text + '</a>');
            remove_button.on('click', this.remove, this);
            this._extra_buttons.appendChild(remove_button);
        }

        if (this._show_assign_me_button) {
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
namespace.PersonPicker = PersonPicker;

}, "0.1", {"requires": ["lazr.picker"]});
