// Helper functions for working with Google Maps v3
//
// Copyright Evan Klitzke, 2011

GS.oldBounds = null;
GS.markers = [];
GS.mapMode = 0;
GS.map = null;
GS.boundsListener = null;

GS.unionStationCoords = {
    "lat": 34.056177,
    "lng": -118.236778
};

GS.formatTime = function (timestamp) {
    var d = new Date(timestamp * 1000);
    var s = d.getFullYear() + "-";
    var m = d.getMonth() + 1;
    if (m < 10) {
        s += "0" + m;
    } else {
        s += m;
    }
    if (d.getDate() < 10) {
        s += "-0" + d.getDate();
    } else {
        s += "-" + d.getDate();
    }
    return s;
};

GS.addMarker = function (map, position, photo) {
    var m = new google.maps.Marker({
        position: position,
        map: map
    });
    if (photo) {
        google.maps.event.addListener(m, 'click', function () {
            var content = '\
<div class="infowindow clickable">\
<img src="/p/' + photo.id + '.m">\
<br>\
Uploaded ' + GS.formatTime(photo.time_created);
            if (photo.user) {
                content += ' by <a href="/user/' + encodeURI(photo.user) + '">' + escape(photo.user) + '</a>';
            }
            content += '</div>';
            map._infoWindow.setContent(content);
            map._infoWindow.open(map, m);
            $('.infowindow').click(function (e) {
                e.preventDefault();
                window.location = "/photo/" + photo.id;
            });
        });
    }
    GS.markers.push(m);
    return m;
};

// reset a map and its associated markers
GS.resetMap = function (map) {
    google.maps.event.clearInstanceListeners(map);
    while (map._markers.length) {
        m = map._markers.pop();
        m.setMap(null);
    }
    return map;
}

// fit a map to bounds, and then run the callback once that's finished; the map
// should be cleared *before* calling this function
GS.fitMapBounds = function (map, bounds, cb) {
    map.fitBounds(bounds);
    var zoomChangeBoundsListener = 
        google.maps.event.addListener(map, "bounds_changed", function(event) {
            // don't let the map get overly zoomed in when we're detecting
            // bounds, anything past 12 is ridiculous (and might happen if
            // there's just a single photo within the bounds, or something like
            // that)
            if (this.getZoom() > 12){
                this.setZoom(12);
            }
            google.maps.event.removeListener(zoomChangeBoundsListener);
            cb();
        });
};

// create a new map
GS.createMap = function (divName, mapOptions, cb) {
    var map = new google.maps.Map(document.getElementById(divName), mapOptions);
    map._markers = [];
    map._oldBounds = null;
    map._infoWindow = new google.maps.InfoWindow();
    if (typeof cb === "function") {
        var zoomChangeBoundsListener = google.maps.event.addListener(map, "bounds_changed", function(event) {
            // don't let the map get overly zoomed in when we're detecting
            // bounds, anything past 12 is ridiculous (and might happen if
            // there's just a single photo within the bounds, or something like
            // that)
            if (this.getZoom() > 12){
                this.setZoom(12);
            }
            google.maps.event.removeListener(zoomChangeBoundsListener);
            cb(map);
        });
    }
    return map;
};

// initialize a cleared "recent" map; this type of map needs the photos up
// front, unlike a "nearby" map which can defer loading of the photos
GS.initializeRecentMap = function (map, photos, updateParams) {
    var bounds = new google.maps.LatLngBounds();
    for (var i = 0; i < photos.length; i++) {
        var p = photos[i];
        if (typeof p.latitude === "number" && typeof p.longitude === "number") {
            var ll = new google.maps.LatLng(p.latitude, p.longitude);
            bounds.extend(ll);
        }
    }
    GS.fitMapBounds(map, bounds, function () {
        GS.updatePoints(map, updateParams);
        google.maps.event.addListener(map, "bounds_changed", function() { GS.updatePoints(map, updateParams); });
    });
};

// initialize a cleared "nearby" map
GS.initializeNearbyMap = function (map, updateParams) {
    GS.updatePoints(map, updateParams);
    google.maps.event.addListener(map, "bounds_changed", function() { GS.updatePoints(map, updateParams); });
};

GS.updatePoints = function (map, params) {
    params = params || {};

    // get the bounds so we can do a server-side search
    var bounds = map.getBounds();
    var ne = bounds.getNorthEast();
    var sw = bounds.getSouthWest();
    params['n'] = ne.lat();
    params['s'] = sw.lat();
    params['e'] = ne.lng();
    params['w'] = sw.lng();

    var ts = (new Date()).valueOf();
    $.get('/photos', params, function(data) {
        if (debug === true) {
            var te = (new Date()).valueOf();
            $("#time_elapsed").html("search completed in <strong>" + parseInt(data.time_ms) + " / " + parseInt(te - ts) + "</strong> ms");
        }

        // remove all of the old markers, by checking if they still exist in
        // the new bounding box
        for (var i = 0; i < map._markers.length; i++) {
            if (!bounds.contains(map._markers[i].getPosition())) {
                map._markers[i].setMap(null);
                map._markers.splice(i, 1);
                i--;
            }
        }

        // add new markers, by checking if they had existed in the previous
        // bounding box
        for (var i = 0; i < data.photos.length; i++) {
            var p = data.photos[i];
            var position = new google.maps.LatLng(p.latitude, p.longitude);
            if (map._oldBounds === null || map._markers.length === 0 || !map._oldBounds.contains(position)) {
                var position = new google.maps.LatLng(p.latitude, p.longitude);
                var m = GS.addMarker(map, position, p);
            }
        }
        
        map._oldBounds = bounds;
    });
};

$(document).ready(function () {

    // read the map mode cookie (default to 0/recent)
    var mmCookie = $.cookie("mm");
    if (mmCookie === null) {
        GS.mapMode = 0;
    } else {
        GS.mapMode = parseInt(mmCookie);
    }
    var map;
    var mapOptions = {mapTypeId: google.maps.MapTypeId.ROADMAP}
    if (GS.mapMode == 0) {
        map = GS.createMap("map_div", mapOptions);
        $.get("/photos", function (data) {
            GS.initializeRecentMap(map, data.photos);
        });
    } else {
        mapOptions.zoom = 10;
        mapOptions.center = new google.maps.LatLng(GS.unionStationCoords["lat"], GS.unionStationCoords["lng"]);
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function (pos) {
                mapOptions.center = new google.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
                map = GS.createMap("map_div", mapOptions, function (map) {
                    GS.initializeNearbyMap(map, {});
                });
            }, function (err) {
                map = GS.createMap("map_div", mapOptions, function (map) {
                    GS.initializeNearbyMap(map, {});
                });
            });
        } else {
            map = GS.createMap("map_div", mapOptions, function (map) {
                GS.initializeNearbyMap(map, {});
            });
        }
    }

    // set up the click handlers for the map mode
    $('.map_mode').click(function () {
        console.info("resetting map");
        GS.resetMap(map);
        if ($(this).text() == 'recent') {
            $.cookie('mm', 0);
            $.get("/photos", function (data) {
                GS.initializeRecentMap(map, data.photos);
            });
        } else if ($(this).text() == 'nearby') {
            $.cookie('mm', 1);
            console.info("initializing nearby map");
            GS.initializeNearbyMap(map, {});
        } else {
            alert('huh?');
        }
        $('.selected_mode').each(function (i, e) {
            $(e).removeClass('selected_mode');
        });
        $(this).addClass('selected_mode');
    });

});
