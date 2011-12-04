$(document).ready(function () {
    console.log('doingit');
    var latlng = new google.maps.LatLng(latitude, longitude);
    var myOptions = {
        zoom: 12,
        center: latlng,
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    var map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);
    var marker = new google.maps.Marker({
        position: latlng,
        map: map,
        // title:"Hello World!"
    });
});
