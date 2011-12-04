$(document).ready(function () {
    var latlng = new google.maps.LatLng(latitude, longitude);
    var mapOptions = {
        zoom: 13,
        center: latlng,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    var map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
    var marker = new google.maps.Marker({
        position: latlng,
        map: map,
    });
});
