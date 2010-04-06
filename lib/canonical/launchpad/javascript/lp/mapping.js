/**
 * Launchpad mapping tools.
 *
 * Map rendering and marker creation depends on the Google GMap2 library.
 *
 * @module lp.mapping
 * @namespace lp.mapping
 * @required Google GMap2
 */
YUI.add('lp.mapping', function(Y) {
    var module = Y.namespace('lp.mapping');

    module.RETURN_FALSE = function() {return false;};
    module.RETURN_NULL = function() {return null;};

    // Replace the crucial GMap functions so that the supporting functions
    // will work if the GMap script is not loaded.
    var gBrowserIsCompatible = module.RETURN_FALSE;
    var gDownloadUrl = module.RETURN_NULL;

    module.has_gmaps = (typeof(GBrowserIsCompatible) == 'function');

    if (module.has_gmaps) {
        // The GMap2 is is loaded; use the real functions.
        // jslint does not like functions that look like classes.
        gBrowserIsCompatible = GBrowserIsCompatible;
        gDownloadUrl = GDownloadUrl;
    }


    /**
     * Add a marker for each participant.
     *
     * @function setMarkersInfoWindow
     * @param {String} data the participant XML.
     * @param {GMap2} map the Google map to add the markers to.
     * @param {GLatLngBounds} required_bounds the boundaries or null.
     * @param {limit} optional max number of markers to set.
     */
    module.setMarkersInfoWindow = function(data, map, required_bounds,
                                            limit) {
        var xml = GXml.parse(data);
        var markers = xml.documentElement.getElementsByTagName("participant");
        var participant = null;

        function attrToProp(attr) {
            participant[attr.name] = attr.value;
        }

        limit = typeof(limit) == 'number' ? limit : markers.length;
        if (markers.length < limit) {
            limit = markers.length;
        }

        for (var i = 0; i < limit; i++) {
            participant = {};
            Y.Array.each(markers[i].attributes, attrToProp);
            var point = new GLatLng(
                parseFloat(participant.lat), parseFloat(participant.lng));
            if (required_bounds) {
                required_bounds.extend(point);
            }
            var marker = new GMarker(point);
            marker.bindInfoWindowHtml(Y.substitute([
                '<div style="text-align: center">',
                '<a href="{url}">{displayname} ({name})</a><br />',
                '{logo_html}<br />',
                'Local time: {local_time}</div>'].join(""),
                participant));
            map.addOverlay(marker);
        }
    };

    /**
     * Add a marker for each participant, and update the zoom level.
     *
     * @function setMarkersInfoWindowForSmallMap
     * @param {String} data the participant XML.
     * @param {GMap2} map the Google map to add the markers to.
     * @param {limit} optional max number of markers to set.
     */
    module.setMarkersInfoWindowForSmallMap = function(data, map, limit) {
        var required_bounds = new GLatLngBounds();
        module.setMarkersInfoWindow(data, map, required_bounds, limit);
        var zoom_level = map.getBoundsZoomLevel(required_bounds);
        // Some browsers do not display the map when the zoom_level is at the
        // end of the range, reduce the zoom_level by 1.
        zoom_level = Math.min(4, zoom_level - 1);
        map.setZoom(zoom_level);
    };

    /**
     * Set the timezone field to the lat-log location.
     *
     * @function setLocation
     * @param {Number} lat a GLatLng.lat bounded number.
     * @param {Number} lng a GLatLng.lng bounded number.
     * @parma {String} geoname the user-name to make geonames requests.
     * @param {String} tz_name the id of the timezone field.
     * @param {String} lat_name the id of the latitude field.
     * @param {String} lng_name the id of the longitude field.
     */
    module.setLocation = function(lat, lng, geoname,
                                   tz_name, lat_name, lng_name) {
        Y.one(Y.DOM.byId(lat_name)).set('value', lat);
        Y.one(Y.DOM.byId(lng_name)).set('value', lng);
        var spinner = Y.one('#tz_spinner');
        spinner.set('src', '/@@/spinner');

        function succeeded() {
            if (request.readyState == 4) {
                if (request.responseText) {
                    var tz = request.responseJSON.timezoneId;
                    Y.one(Y.DOM.byId(tz_name)).set('value', tz);
                    spinner.set('src', '/@@/nospin');
                }
            }
        }

        var url = 'http://ba-ws.geonames.net/timezoneJSON' +
            '?username=' + geoname + '&lat=' + lat + '&lng=' + lng;
        // This is a cross-site script request.
        var request = new JSONScriptRequest();
        request.open("GET", url);
        request.onreadystatechange = succeeded;
        request.send(null);
    };

    /**
     * Show/hide all small maps in pages.
     *
     * The state is stored as ``small_maps`` in the launchpad_views cookie.
     *
     * @function toggleShowSmallMaps
     * @param {Event} e the event for this callback.
     */
    module.toggleShowSmallMaps = function (checkbox) {
        var is_shown = checkbox.get('checked');
        Y.lp.launchpad_views.set('small_maps', is_shown);
        var display = is_shown ? 'block' : 'none';
        var maps = Y.all('.small-map');
        maps.each(function(map) {map.setStyle('display', display);});
        if (is_shown && !module.has_gmaps) {
            // The server must add the Google GMap2 dependencies to the page.
            window.location.reload();
        }
    };

    /**
     * Add a checkbox to show/hide all small maps in pages.
     *
     * @function setupShowSmallMapsControl
     * @param {String} div_id the CSS3 id of the div that controls the map.
     */
    module.setupShowSmallMapsControl = function (div_id) {
        var show_small_maps = Y.lp.launchpad_views.get('small_maps');
        var checkbox = Y.Node.create(
            '<input type="checkbox" name="show_small_maps" />');
        checkbox.set(
            'checked', show_small_maps);
        checkbox.on(
            'click', function(e) {module.toggleShowSmallMaps(checkbox);});
        var label_text = Y.Node.create('Display map');
        var label = Y.Node.create('<label></label>');
        label.appendChild(checkbox);
        label.appendChild(label_text);
        var action_div = Y.one(div_id);
        action_div.appendChild(label);
        if (!show_small_maps) {
            module.toggleShowSmallMaps(checkbox);
        }
    };

    /**
     * Create a small map with the launchpad default configuration.
     *
     * @function getSmallMap
     * @param {String} div_id the id of the map div.
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     * @return {GMap2} the Google map
     */
    module.getSmallMap = function(div_id, center_lat, center_lng) {
        var mapdiv = Y.DOM.byId(div_id);
        mapdiv.style.width = '400px';
        var map = new GMap2(mapdiv);
        var center = new GLatLng(center_lat, center_lng);
        map.setCenter(center, 1);
        map.setMapType(G_NORMAL_MAP);
        return map;
    };

    /**
     * Create a small map of where a person is located.
     *
     * @function renderPersonMapSmall
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    module.renderPersonMapSmall = function(center_lat, center_lng) {
        module.setupShowSmallMapsControl('#person_map_actions');
        if (!gBrowserIsCompatible()) {
            return;
        }
        var map = module.getSmallMap(
            'person_map_div', center_lat, center_lng);
        map.addControl(new GSmallZoomControl());
        var center = new GLatLng(center_lat, center_lng);
        var marker = new GMarker(center);
        map.addOverlay(marker);
    };

    /**
     * Create a small map of where a team's members are located. The map is
     * limited to 24 members.
     *
     * @function renderTeamMapSmall
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    module.renderTeamMapSmall = function(center_lat, center_lng) {
        module.setupShowSmallMapsControl('#team_map_actions');
        if (!gBrowserIsCompatible()) {
            return;
        }
        var team_map = module.getSmallMap(
            'team_map_div', center_lat, center_lng);
        gDownloadUrl("+mapdataltd", function(data) {
            module.setMarkersInfoWindowForSmallMap(data, team_map);
            });
    };

    /**
     * Create a large map with the launchpad default configuration.
     *
     * @function getLargeMap
     * @param {String} div_id the id of the map div.
     * @return {GMap2} The Google map
     */
    module.getLargeMap = function(div_id) {
        var mapdiv = Y.DOM.byId(div_id);
        var mapheight = (parseInt(mapdiv.offsetWidth, 10) / 16 * 9);
        mapheight = Math.min(mapheight, Y.DOM.winHeight() - 180);
        mapheight = Math.max(mapheight, 400);
        mapdiv.style.height = mapheight + 'px';
        var map = new GMap2(mapdiv);
        map.setMapType(G_HYBRID_MAP);
        map.addControl(new GLargeMapControl());
        map.addControl(new GMapTypeControl());
        map.addControl(new GScaleControl());
        map.enableScrollWheelZoom();
        var overview_control = new GOverviewMapControl();
        map.addControl(overview_control);
        GEvent.addListener(map, 'zoomend', function(old, current) {
            try {
                if (current < 3) {
                    overview_control.hide();
                } else {
                    overview_control.show();
                }
            } catch(e) {
                // Google removed this undocumented method.
            }
        });
        return map;
    };

    /**
     * Create a large map of where a team's members are located.
     *
     * @function renderTeamMap
     * @param {Number} min_lat the minimum GLatLng.lat bounded number.
     * @param {Number} max_lat the maximum GLatLng.lat bounded number.
     * @param {Number} min_lng the minimum GLatLng.lng bounded number.
     * @param {Number} max_lng the maximum GLatLng.lng bounded number.
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    module.renderTeamMap = function(min_lat, max_lat, min_lng, max_lng,
                                     center_lat, center_lng) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var team_map = module.getLargeMap("team_map_div");
        var center = new GLatLng(center_lat, center_lng);
        team_map.setCenter(center, 0);
        var sw = new GLatLng(min_lat, min_lng);
        var ne = new GLatLng(max_lat, max_lng);
        var required_bounds = new GLatLngBounds(sw, ne);
        var zoom_level = team_map.getBoundsZoomLevel(required_bounds);
        // Some browsers do not display the map when the zoom_level is at
        // the end of the range, reduce the zoom_level by 1.
        zoom_level = Math.min(
            G_HYBRID_MAP.getMaximumResolution(), zoom_level - 1);
        team_map.setZoom(zoom_level);
        gDownloadUrl("+mapdata", function(data) {
            module.setMarkersInfoWindow(data, team_map);
            });
    };

    /**
     * Create a large, markable map of where a person is located.
     *
     * @function renderPersonMap
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     * @param {String} displayname the user's display name.
     * @param {String} name the user's launchpad id.
     * @param {String} logo_html the markup to display the user's logo.
     * @param {String} geoname the identity used to access ba-ws.geonames.net.
     * @param {String} tz_name the id of the timezone field.
     * @param {String} lat_name the id of the latitude field.
     * @param {String} lng_name the id of the longitude field.
     * @param {number} zoom the initial zoom-level.
     * @param {Boolean} show_marker Show the marker for the person.
     */
    module.renderPersonMap = function(center_lat, center_lng, displayname,
                                       name, logo_html, geoname, lat_name,
                                       lng_name, tz_name, zoom, show_marker) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var map = module.getLargeMap('map_div');
        var center = new GLatLng(center_lat, center_lng);
        map.setCenter(center, zoom);
        var marker = new GMarker(center, {draggable: true});
        marker.bindInfoWindowHtml(Y.substitute(
            '<div style="text-align: center">' +
            '<strong>{displayname}</strong><br />' +
            '{logo_html}<br />({name})</div>',
            {displayname: displayname, logo_html: logo_html, name: name}),
            {maxWidth: 120});

        GEvent.addListener(marker, "dragend", function() {
            var point = marker.getLatLng();
            module.setLocation(
                point.lat(), point.lng(), geoname,
                tz_name, lat_name, lng_name);
        });

        GEvent.addListener(marker, "dragstart", function() {
            marker.closeInfoWindow();
        });

        map.addOverlay(marker);
        if (!show_marker) {
            marker.hide();
        }

        GEvent.addListener(map, "zoomend", function() {
            marker.closeInfoWindow();
        });

        GEvent.addListener(map, "click", function(overlay, point) {
            marker.setPoint(point);
            if (marker.isHidden()) {
                marker.show();
                map.panTo(point);
            }
            module.setLocation(
                point.lat(), point.lng(), geoname,
                tz_name, lat_name, lng_name);
        });
    };
}, "0.1", {"requires":["node", "dom", "substitute", "lp"]});
