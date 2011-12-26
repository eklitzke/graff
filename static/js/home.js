$(document).ready(function () {
    $('#imgfield').change(function () {
        $('#imgform').submit();
    });
    /*
    if (markers) {
        var mapOptions = {
            center: bounds.getCenter(),
            mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        var map = new google.maps.Map(document.getElementById("uploads_map"), mapOptions);

        // Try to fit the map to a reasonable boundary. But if the map wants to
        // zoom in too closely (e.g. one person has uploaded a bunch of photos
        // from the same place, zoom the map out to a somewhat reasonable level.
        map.fitBounds(bounds);
        var zoomChangeBoundsListener = 
            google.maps.event.addListener(map, 'bounds_changed', function(event) {
                if (this.getZoom() > 12){
                    this.setZoom(12);
                }
                google.maps.event.removeListener(zoomChangeBoundsListener);
            });
        for (var i = 0; i < markers.length; i++) {
            var marker = new google.maps.Marker({
                position: markers[i],
                map: map
            });
        }
    }
    */
});
