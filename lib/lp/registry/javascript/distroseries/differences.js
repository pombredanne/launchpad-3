/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * DistroSeries Initialization.
 *
 * @module lp.registry.distroseries
 * @submodule differences
 */

YUI.add('lp.registry.distroseries.differences', function(Y) {

Y.log('loading lp.registry.distroseries.differences');

var namespace = Y.namespace('lp.registry.distroseries.differences');

var widgets = Y.lp.registry.distroseries.widgets;
var formwidgets = Y.lp.app.formwidgets;


var PACKAGESET_FIELD = "field.packageset",
    PACKAGESET_FIELD_SELECTOR = "input[name=" + PACKAGESET_FIELD + "]";


/**
 * Return an array of the package-set IDs that are configured in the
 * current window's query string.
 *
 * @param {String} qs The query string, typically obtained from
 *     window.location.search.
 */
var get_package_sets_in_query_string = function(qs) {
    var query = Y.QueryString.parse(qs.replace(/^[?]/, ""));
    /* Y.QueryString.parse() tries to be helpful and convert
       numeral strings into numbers... but we don't want that,
       so we have to convert back again. */
    var packagesets = query[PACKAGESET_FIELD];
    var n2s = function(n) { return n.toString(10); };
    if (Y.Lang.isArray(packagesets)) {
        return packagesets.map(n2s);
    }
    else if (Y.Lang.isValue(packagesets)) {
        return [n2s(packagesets)];
    }
    else {
        return [];
    }
};


/**
 * Wire up a package-set picker that update the given form.
 *
 * @param {Y.Node} origin The node that, when clicked, should activate
 *     the picker.
 * @param {Y.Node} form The form that the picker should update.
 */
var connect_packageset_picker = function(origin, form) {
    /* XXX: GavinPanella 2011-07-19 bug=???: PackagesetPickerWidget
       needs to render into a container. This should not be
       required. */
    var picker_table =
        Y.Node.create("<table><tbody /></table>");
    var picker =
        new widgets.PackagesetPickerWidget()
            .set("name", "packagesets")
            .set("size", 5)
            .set("multiple", true)
            .render(picker_table.one("tbody"));

    /* XXX: GavinPanella 2011-07-19 bug=???:
       PackagesetPickerWidget.add_distroseries() accepts only this
       odd-looking object. It would be more convenient and less
       surprising if it also accepted an lp.client.Entry. */
    picker.add_distroseries({
        api_uri: LP.cache.context.self_link,
        title: LP.cache.context.title,
        value: LP.cache.context.self_link
    });

    /* Buttons */
    var submit_button = Y.Node.create(
        '<button type="submit" class="lazr-pos lazr-btn" />')
           .set("text", "OK");
    var cancel_button = Y.Node.create(
        '<button type="button" class="lazr-neg lazr-btn" />')
           .set("text", "Cancel");

    /* When the form overlay is submitted the search filter form is
       modified and submitted. */
    var submit_callback = function(data) {
        // Remove all packagesets information previously recorded.
        form.all(PACKAGESET_FIELD_SELECTOR).remove();
        if (data.packagesets !== undefined) {
            Y.each(data.packagesets, function(packageset) {
                form.append(
                    Y.Node.create('<input type="hidden" />')
                        .set("name", PACKAGESET_FIELD)
                        .set("value", packageset));
            });
        }
        form.submit();
    };

    /* Form overlay. */
    var overlay = new Y.lazr.FormOverlay({
        align: {
            /* Align the centre of the overlay with the centre of the
               origin node. */
            node: origin,
            points: [
                Y.WidgetPositionAlign.CC,
                Y.WidgetPositionAlign.CC
            ]
        },
        headerContent: "<h2>Select package sets</h2>",
        form_content: picker_table,
        form_submit_button: submit_button,
        form_cancel_button: cancel_button,
        form_submit_callback: submit_callback,
        visible: false
    });
    overlay.render();

    var realign_overlay = function() {
        /* Trigger alignment and constrain to the viewport. Should
           these not happen automatically? Perhaps there's a bad
           interaction between widget-position-align and
           widget-position-constrain? */
        overlay.set("align", overlay.get("align"));
        overlay.constrain(null, true);
    };
    overlay.after("visibleChange", realign_overlay);
    Y.on("windowresize", realign_overlay);

    var initialize_picker = function() {
        // Set the current selection from the query string.
        picker.set(
            "choice", get_package_sets_in_query_string(
                window.location.search));
    };
    /* XXX: GavinPanella 2011-07-20 bug=???: We should be able to
       listen to choicesChange events from the picker widget but
       they're not fired consistently. Instead we initialize when
       showing the overlay, which is prone to a race condition (it may
       update the selection before the packageset picker has been
       populated with choices. */
    overlay.after("visibleChange", function(e) {
        // Only initialize when going from hidden -> visible.
        if (e.newVal) { initialize_picker(); }
    });

    /* Convert the content of the origin into a js-action link, and
       show the overlay when its clicked. */
    var link = Y.Node.create('<a class="js-action sprite edit" />');
    link.set("innerHTML", origin.get("innerHTML"));
    link.on("click", function() { overlay.show(); });
    origin.empty().append(link);

    // XXX: For Development Only.
    window.overlay = overlay;
    window.picker = picker;
};


// Exports.
namespace.connect_packageset_picker = connect_packageset_picker;


}, "0.1", {
    "requires": [
        "node",
        "querystring-parse",
        "lazr.formoverlay",
        "lp.app.formwidgets",
        "lp.registry.distroseries.widgets"
    ]});
