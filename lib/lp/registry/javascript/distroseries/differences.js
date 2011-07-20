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


var getPackageSetsInQueryString = function(qs) {
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


var setupPackageSetPicker = function(packagesets_header, form) {
    /* XXX: GavinPanella 2011-07-19 bug=???: PackagesetPickerWidget
       needs to render into a container. This should not be
       required. */
    var packageset_picker_table =
        Y.Node.create("<table><tbody /></table>");
    var packageset_picker =
        new widgets.PackagesetPickerWidget()
            .set("name", "packagesets")
            .set("size", 5)
            .set("multiple", true)
            .render(packageset_picker_table.one("tbody"));

    /* XXX: GavinPanella 2011-07-19 bug=???:
       PackagesetPickerWidget.add_distroseries() accepts only this
       odd-looking object. It would be more convenient and less
       surprising if it also accepted an lp.client.Entry. */
    packageset_picker.add_distroseries({
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
            /* Align the top-centre of the overlay with the
               bottom-centre of the invoking object (i.e. the header
               cell). */
            node: packagesets_header,
            points: [
                Y.WidgetPositionAlign.TC,
                Y.WidgetPositionAlign.BC
            ]
        },
        headerContent: "<h2>Select package sets</h2>",
        form_content: packageset_picker_table,
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
        packageset_picker.set(
            "choice", getPackageSetsInQueryString(
                window.location.search));
    };
    overlay.after("visibleChange", initialize_picker);

    /* Show the overlay when the packagesets header is clicked. */
    packagesets_header.on("click", function() { overlay.show(); });

    // XXX: For Development Only.
    window.overlay = overlay;
    window.picker = packageset_picker;
};


// Exports.
namespace.setupPackageSetPicker = setupPackageSetPicker;


}, "0.1", {
    "requires": [
        "node",
        "querystring-parse",
        "lazr.formoverlay",
        "lp.app.formwidgets",
        "lp.registry.distroseries.widgets"
    ]});
