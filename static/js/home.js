$(document).ready(function () {
    $('#imgfield').change(function () {
        $('#imgform').submit();
    });
    if (center) {
        var mapOptions = {
            center: center,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        var map = new google.maps.Map(document.getElementById("uploads_map"), mapOptions);
        map.fitBounds(bounds);
        for (var i = 0; i < markers.length; i++) {
            var marker = new google.maps.Marker({
                position: markers[i],
                map: map
            });
        }
    }
});
