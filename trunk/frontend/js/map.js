/* A GMap-management object.  Simplifies viewpoint and marker geocoding. */
function SimpleMap(div) {
  this.div_ = div;
  this.defaultZoom_ = 12;

  if (GBrowserIsCompatible()) {
    this.map_ = new GMap2(div);
    this.map_.setCenter(new GLatLng(40, -25), me.defaultZoom_);
    this.map_.enableContinuousZoom();
    this.map_.enableScrollWheelZoom();
    this.geocoder_ = new GClientGeocoder();
    if (false) {
      this.icon_ = new GIcon(G_DEFAULT_ICON, "/images/markers/red.png");
      this.icon_.iconSize.width = 32;
      this.icon_.iconSize.height = 32;
      this.icon_.iconAnchor.x = 15;
      this.icon_.iconAnchor.y = 31;
    }
    return this;
  } else {
    return null;
  }
}

SimpleMap.prototype.setCenterGeocode = function(locationString) {
  var me = this;
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.map_.setCenter(latLng, me.defaultZoom_);
    }
  });
}

SimpleMap.prototype.addMarker = function(lat, lng) {
  var latLng = new GLatLng(lat, lng);
  this.map_.addOverlay(new GMarker(latLng, this.icon_));
}

SimpleMap.prototype.addMarkerGeocode = function(locationString) {
  var me = this;
  // TODO(paul): Use .getLocations() method instead, to get accuracy rating.
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.addMarker(latLng.lat(), latLng.lng());
    }
  });
}
