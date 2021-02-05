#API  (Note: this must be the first thing in the script)

# Please, for the love, don't use this yet if you don't know what you're doing.


if True:

    mapData = model.DynamicData()
    mapData.people = q.BlueToolbarReport("PrimaryAddress")
    mapData.cesiumKey = model.Setting("CesiumKey", "")
    
    template = """
    
    <style>
    body div.container-fluid#main {
        width: 100% !important;
        padding: 0;
        margin: 0;
        color: #ddd;
    }
    div#page-header {
        display: none;
    }
    
    body .box-content {
        padding: 0;
        background-color: black;
        border-width: 0;
    }
    
    html body {
        background-color:  black;
    }
    
    .box.box-responsive {
        border-width: 0;
    }
    #cesiumContainer {
        height: 100%;
        height: calc(100vh - 50px);
    }
    </style>
    
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.78/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.78/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    
    <div id="cesiumContainer" class="fullSize"></div>
    <div id="loadingOverlay"><h1>Loading...</h1></div>
    <div id="toolbar"></div>
    
    <script>
    Cesium.Ion.defaultAccessToken = '{{{cesiumKey}}}';
    const viewer = new Cesium.Viewer('cesiumContainer', {
            animation : false,
            fullscreenButton: false, // wil be manually created later, to put it into the toolbar
            geocoder : false,
            infoBox: true,
            skyAtmosphere: false,
            skyBox: false,
            timeline : false,
            scene: {
                globe: {
                    enableLighting: true
                }
            }
        });
        
        //var data = Cesium.CzmlDataSource.load('/pythonapi/mapify?t=czml');
        
        var flyHome = function () {
            viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(-75.169899, 39.947262, 85000.0), // TODO replace with church lat/lng setting
                duration:4
            });
        };
    
        entities = {};
        geo = new Cesium.BingMapsGeocoderService({key: 'INSERT_YOUR_BING_KEY_HERE'});
        limit = 1000;
        function geocodeAndPlacePerson(person) {
            if (limit-- <= 0) {
                console.log("Geocoding limit reached.  Cannot continue.");
                return;
            }
            
            geo.geocode(person.address).then((res) => placeEntity(person, res), (res) => console.error(res))
        }
        function placeEntity(person, geoResult) {
            window.geoRes = geoResult;
        
            if (geoResult.length < 1) {
                console.log("Could not find", person);
                return
            }
            
            let pos;
                
            if (geoResult[0].destination.constructor.name === "Rectangle") {
                pos = Cesium.Cartographic.toCartesian(Cesium.Rectangle.center(geoResult[0].destination));
            } else {
                pos = geoResult[0].destination;
            }
            
            window.geoPosition = pos;
            
            console.log(person, geoResult);
            
            entities["p" + person.peopleId] = viewer.entities.add({
                position: pos,
                name: person.name,
                point: {
                    pixelSize: 20,
                    color: new Cesium.Color(0, 1, 0, 0.5)
                },
            });
            
        }
        
        {{#each people}}
        geocodeAndPlacePerson({
            address: "{{PrimaryAddress}}, {{CityStateZip}}",
            name: '{{PreferredName}} {{LastName}}',
            peopleId: {{PeopleId}}
        })
        {{/each}}
        
        
        viewer.homeButton.viewModel._command = Cesium.createCommand(flyHome);
    
        //viewer.dataSources.add(data).then(flyHome);
    
        viewer.infoBox.frame.sandbox = "allow-same-origin allow-top-navigation allow-pointer-lock allow-popups allow-forms allow-scripts";
    
        viewer.baseLayerPicker.viewModel.selectedImagery = viewer.baseLayerPicker.viewModel.imageryProviderViewModels[8];
        
    </script>
    
    
    """
    
    print model.RenderTemplate(template, mapData)