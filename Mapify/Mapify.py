#API  (Note: this must be the first thing in the script)

import urllib
import json
import clr
from System.Collections.Generic import Dictionary

geoLatEV = "geoLat"
geoLngEV = "geoLng"
geoHashEV = "geoHsh"

googleRegionBias = "us"

if model.FromMorningBatch or Data.action == "geocode":
    # Geocode profiles
    
    googleKey = model.Setting("GoogleGeocodeAPIKey","")
    
    def getGoogleGeocode(address):
        params = {
            'address': address,
            'key': googleKey,
            'region': googleRegionBias
            }
        req = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.urlencode(params)
        geo = json.loads(model.RestGet(req, {}))
        
        if len(geo['results']) < 1:
            return None
            
        else:
            return {
                'lat': geo['results'][0]['geometry']['location']['lat'],
                'lng': geo['results'][0]['geometry']['location']['lng'],
                'precision': geo['results'][0]['geometry']['location_type']
                }

    
    def doAGeocode(days):
        # Figure out target list
        
        # TODO: search by hash.  Ideally, have SQL do hashing. 
        qInv = """
        (
        	NOT HasPeopleExtraField = '{0}'
        	AND NOT HasFamilyExtraField = '{0}'
        )
        AND 
        (
        	RecentAttendCount( Days={1} ) > 1
        	OR IsRecentGiver( Days={1} ) = 1[True]
        )
        AND 
        (
        	
        	(
        		PrimaryCountry <> '*united sta*'
        		AND PrimaryCountry <> '*usa*'
        	)
        	OR PrimaryZip <> ''
        )
        AND PrimaryBadAddrFlag = 0[False]
        AND PrimaryAddress <> ''
        """.format(geoHashEV, days)
        
        i = 0
        
        for p in q.QueryList(qInv):
            i+=1
            print "<p>{}</p>".format(p.Name)
            
            # TODO verify that EVs are still missing--haven't been added to family already in this pass. 
            
            useFamily = False
            country = p.CountryName or ""
            
            if p.CityName == None and p.ZipCode == None:
                useFamily == True
                country = p.Family.CountryName or ""
            
            address = (p.FullAddress + " " + country).strip()
            
            geo = None
            
            geo = getGoogleGeocode(address)
            print "<p><b>{}</b></p>".format(geo)
            
            if geo == None:
                model.AddExtraValueText(p.PeopleId, geoHashEV, "Failed")
                # if useFamily:
                #     #p.Family.AddEditExtraText(geoHashEV, "Failed")
                #     model.AddExtraValueText
                # else:
                #     #p.AddEditExtraText(geoHashEV, "Failed")
                #     model.AddExtraValueText(p.PeopleId, geoHashEV, "Failed")
            else:
                model.AddExtraValueText(p.PeopleId, geoHashEV, "Success")
                model.AddExtraValueText(p.PeopleId, geoLatEV, str(geo['lat']))
                model.AddExtraValueText(p.PeopleId, geoLngEV, str(geo['lng']))
                # if useFamily:
                #     #p.Family.AddEditExtraText(geoLatEV, str(geo['lat']))
                #     #p.Family.AddEditExtraText(geoLngEV, str(geo['lng']))
                #     #p.Family.AddEditExtraText(geoHashEV, "Success")
                # else:
                #     #p.AddEditExtraText(geoLatEV, str(geo['lat']))
                #     #p.AddEditExtraText(geoLngEV, str(geo['lng']))
                #     #p.AddEditExtraText(geoHashEV, "Success")
    
    
    doAGeocode(95)

elif True:

    mapData = model.DynamicData()
    mapData.cesiumKey = model.Setting("CesiumKey", "")
    
    mapData.pts = Dictionary[int, Dictionary[str, object]]()
    locationIndx = 0
    for p in q.BlueToolbarReport():
        lat = model.ExtraValueText(p.PeopleId, geoLatEV)
        lng = model.ExtraValueText(p.PeopleId, geoLngEV)
        
        if lat == "" or lng == "":
            continue;
        
        aHash = hash(p.FullAddress)
        
        if not mapData.pts.ContainsKey(aHash):
            mapData.pts.Add(aHash, Dictionary[str, object]({
                'cnt': 0, 
                'hash': aHash, 
                'families': Dictionary[int, object](), 
                'lat': lat,
                'lng': lng,
                }))
                
        if not mapData.pts[aHash]['families'].ContainsKey(p.Family.FamilyId):
            mapData.pts[aHash]['families'][p.Family.FamilyId] = []
            
        mapData.pts[aHash]['families'][p.Family.FamilyId].Add(p.PeopleId)
        mapData.pts[aHash]['cnt'] += 1
    
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
        
        {{#each pts}}
        entities[{{@index}}] = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees({{this.lng}}, {{this.lat}}, 0),
            name: "Location {{@index}}",
            point: {
                pixelSize: Math.sqrt({{this.cnt}}) * 10,
                color: new Cesium.Color(0, 1, 0, 0.5)
            },
        });
        {{/each}}
        
        
        viewer.homeButton.viewModel._command = Cesium.createCommand(flyHome);
    
        //viewer.dataSources.add(data).then(flyHome);
    
        viewer.infoBox.frame.sandbox = "allow-same-origin allow-top-navigation allow-pointer-lock allow-popups allow-forms allow-scripts";
    
        viewer.baseLayerPicker.viewModel.selectedImagery = viewer.baseLayerPicker.viewModel.imageryProviderViewModels[8];
        
    </script>
    
    
    """
    
    print model.RenderTemplate(template, mapData)