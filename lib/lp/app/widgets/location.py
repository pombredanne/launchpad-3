# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0702

__metaclass__ = type
__all__ = [
    'ILocationWidget',
    'LocationWidget',
    ]

from lazr.restful.utils import safe_js_escape
from z3c.ptcompat import ViewPageTemplateFile
from zope.app.form import InputWidget
from zope.app.form.browser.interfaces import IBrowserWidget
from zope.app.form.browser.widget import BrowserWidget
from zope.app.form.interfaces import (
    IInputWidget,
    WidgetInputError,
    )
from zope.component import getUtility
from zope.formlib import form
from zope.interface import implements
from zope.schema import (
    Choice,
    Float,
    )

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag,
    IMultiLineWidgetLayout,
    )
from lp.app.browser.tales import ObjectImageDisplayAPI
from lp.app.validators import LaunchpadValidationError
from lp.registry.interfaces.location import IObjectWithLocation
from lp.services.geoip.interfaces import IGeoIPRecord


class ILocationWidget(IInputWidget, IBrowserWidget, IMultiLineWidgetLayout):
    """A widget for selecting a location and time zone."""


class LocationValue:
    """A location passed back from a LocationWidget.

    This is a single object which contains the latitude, longitude and time
    zone of the location.
    """

    def __init__(self, latitude, longitude, time_zone):
        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone


class LocationWidget(BrowserWidget, InputWidget):
    """See `ILocationWidget`."""
    implements(ILocationWidget)

    __call__ = ViewPageTemplateFile("templates/location.pt")

    def __init__(self, context, request):
        # This widget makes use of javascript for googlemaps and
        # json-handling, so we flag that in the request so that our
        # base-layout includes the necessary javascript files.
        request.needs_json = True
        super(LocationWidget, self).__init__(context, request)
        fields = form.Fields(
            Float(__name__='latitude', title=_('Latitude'), required=False),
            Float(__name__='longitude', title=_('Longitude'), required=False),
            Choice(
                __name__='time_zone', vocabulary='TimezoneName',
                title=_('Time zone'), required=True,
                description=_(
                    'Once the time zone is correctly set, events '
                    'in Launchpad will be displayed in local time.')))
        # This will be the initial zoom level and center of the map.
        self.zoom = 2
        self.center_lat = 15.0
        self.center_lng = 0.0
        # By default, we will not show a marker initially, because we are
        # not absolutely certain of the location we are proposing.  The
        # variable is a number that will be passed to JavaScript and
        # evaluated as a boolean.
        self.show_marker = 0
        data = {
            'time_zone': None,
            'latitude': None,
            'longitude': None,
            }
        # If we are creating a record for ourselves, then we will default to
        # a location GeoIP guessed, and a higher zoom.
        if getUtility(ILaunchBag).user == context.context:
            geo_request = IGeoIPRecord(request)
            self.zoom = 7
            self.center_lat = geo_request.latitude
            self.center_lng = geo_request.longitude
            data['time_zone'] = geo_request.time_zone
        current_location = IObjectWithLocation(self.context.context)
        if current_location.latitude is not None:
            # We are updating a location.
            data['latitude'] = current_location.latitude
            data['longitude'] = current_location.longitude
            self.center_lat = current_location.latitude
            self.center_lng = current_location.longitude
            self.zoom = 9
            self.show_marker = 1
        if current_location.time_zone is not None:
            # We are updating a time zone.
            data['time_zone'] = current_location.time_zone
        self.initial_values = data
        widgets = form.setUpWidgets(
            fields, self.name, context, request, ignore_request=False,
            data=data)
        self.time_zone_widget = widgets['time_zone']
        self.latitude_widget = widgets['latitude']
        self.longitude_widget = widgets['longitude']

    @property
    def map_javascript(self):
        """The Javascript code necessary to render the map."""
        person = self.context.context
        replacements = dict(
            center_lat=self.center_lat,
            center_lng=self.center_lng,
            displayname=safe_js_escape(person.displayname),
            name=person.name,
            logo_html=ObjectImageDisplayAPI(person).logo(),
            geoname=config.launchpad.geonames_identity,
            lat_name=self.latitude_widget.name,
            lng_name=self.longitude_widget.name,
            tz_name=self.time_zone_widget.name,
            zoom=self.zoom,
            show_marker=self.show_marker)
        return """
            <script type="text/javascript">
                LPS.use('node', 'lp.app.mapping', function(Y) {
                    function renderMap() {
                        Y.lp.app.mapping.renderPersonMap(
                            %(center_lat)s, %(center_lng)s, %(displayname)s,
                            '%(name)s', '%(logo_html)s', '%(geoname)s',
                            '%(lat_name)s', '%(lng_name)s', '%(tz_name)s',
                            %(zoom)s, %(show_marker)s);
                     }
                     Y.on("domready", renderMap);
                });
            </script>
            """ % replacements

    def hasInput(self):
        """See `IBrowserWidget`.

        Return True if time zone or latitude widgets have input.
        """
        return (self.time_zone_widget.hasInput()
                or self.latitude_widget.hasInput())

    def getInputValue(self):
        """See `IBrowserWidget`.

        Return a `LocationValue` object containing the latitude, longitude and
        time zone chosen.
        """
        self._error = None
        time_zone = self.time_zone_widget.getInputValue()
        latitude = None
        longitude = None
        if self.latitude_widget.hasInput():
            latitude = self.latitude_widget.getInputValue()
        if self.longitude_widget.hasInput():
            longitude = self.longitude_widget.getInputValue()
        if time_zone is None:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide a valid time zone.')))
            raise self._error
        if ((latitude is None and longitude is not None)
            or (latitude is not None and longitude is None)):
            # We must receive both a latitude and a longitude.
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide both latitude and longitude.')))
            raise self._error
        if latitude is not None:
            if abs(latitude) > 90 or abs(longitude) > 180:
                # We need latitude and longitude within range.
                self._error = WidgetInputError(
                    self.name, self.label, LaunchpadValidationError(
                        _('Please provide a more realistic latitude '
                          'and longitude.')))
                raise self._error
        return LocationValue(latitude, longitude, time_zone)
