var map = L.map('map').setView([53.3498, -6.2603], 10)
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);

    //the pop up thing for the map :)
    var popup = L.popup();
    function onMapClick(e) {
        popup
            .setLatLng(e.latlng) 
            .setContent("You have selected " + e.latlng.toString())
            .openOn(map);
    }
    map.on('click', onMapClick);

    //inputing the latlng into the input feild
    function userInput2(e){
    document.getElementById('latlng3').value = e.latlng;
    }
    map.on('click', userInput2);