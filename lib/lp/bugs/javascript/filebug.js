/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for the file bug pages.
 *
 * @module bugs
 * @submodule filebug
 */
YUI.add('lp.bugs.filebug', function(Y) {

var namespace = Y.namespace('lp.bugs.filebug');

// For tests.
var skip_animation;

var setup_filebug = function(skip_anim) {
    skip_animation = skip_anim;
    if (LP.cache.enable_bugfiling_duplicate_search) {
        Y.lp.bugs.filebug_dupefinder.setup_dupe_finder();
    }
    Y.lp.bugs.filebug_dupefinder.setup_dupes();
    // Only attempt to wire up the file bug form if the form is rendered.
    var filebugform = Y.one('#filebug-form');
    var bugreportingform = Y.one('#bug-reporting-form');
    if (Y.Lang.isValue(filebugform) || Y.Lang.isValue(bugreportingform)) {
        var search_button =
            Y.one(Y.DOM.byId('field.actions.projectgroupsearch'));
        if (Y.Lang.isValue(search_button )) {
            search_button.set('value', 'Check again');
        }
        set_default_privacy_banner();
        setup_information_type();
        setup_security_related();
        setupChoiceWidgets();
    }
};

var set_default_privacy_banner = function() {
    var itypes_table = Y.one('.radio-button-widget');
    var val = null;
    if (itypes_table) {
        val = itypes_table.one(
            "input[name='field.information_type']:checked").get('value');
    } else {
        val = 'PUBLIC'; 
    }
    
    if (LP.cache.bug_private_by_default) {
        var filebug_privacy_text = "This report will be private. " +
            "You can disclose it later.";
        update_privacy_banner(true, filebug_privacy_text);
    } else {
        update_banner_from_information_type(val);
    }
};

var update_privacy_banner = function(show, banner_text) {
    var banner = Y.lp.app.banner.privacy.getPrivacyBanner(
        banner_text, skip_animation);
    if (show) {
        banner.show();
    } else {
        banner.hide();
    }
};

var get_new_banner_text = function(value) {
    var info_type_descriptions = {};
    Y.Array.forEach(LP.cache.information_type_data, function(item) {
        info_type_descriptions[item.value] = item.name;
    });
    var text_template = "This report contains {info_type} information." +
        " You can change the information type later.";
    value = info_type_descriptions[value];
    return Y.Lang.substitute(text_template, {'info_type': value});
};

var update_banner_from_information_type = function(value) {
    var banner_text = get_new_banner_text(value);
    var is_private = (Y.Array.indexOf(
        LP.cache.private_types, value) >= 0);
    update_privacy_banner(is_private, banner_text);
};

var setup_information_type = function() {
    var itypes_table = Y.one('.radio-button-widget');
    if (!Y.Lang.isValue(itypes_table)) {
        return;
    }


    itypes_table.delegate('change', function() {
        update_banner_from_information_type(this.get('value'));
    }, "input[name='field.information_type']");
};

var setupChoiceWidgets = function() {
    Y.lp.app.choice.addPopupChoice('status', LP.cache.bugtask_status_data);
    Y.lp.app.choice.addPopupChoice(
        'importance', LP.cache.bugtask_importance_data);
    Y.lp.app.choice.addPopupChoiceForRadioButtons(
        'information_type', LP.cache.information_type_data, true);
};

var setup_security_related = function() {
    var security_related = Y.one('[id="field.security_related"]');
    if (!Y.Lang.isValue(security_related)) {
        return;
    }
    var notification_text = "This report will be private " +
                           "because it is a security " +
                           "vulnerability. You can " +
                           "disclose it later.";
    security_related.on('change', function() {
        var checked = security_related.get('checked');
        if (checked) {
            update_privacy_banner(true, notification_text);
        } else {
            set_default_privacy_banner();
        }
    });
};

namespace.setup_filebug = setup_filebug;

}, "0.1", {"requires": [
    "base", "node", "event", "node-event-delegate", "lazr.choiceedit",
    "lp.app.banner.privacy", "lp.app.choice",
    "lp.bugs.filebug_dupefinder"]});
