# API  (Note: this must be the first thing in the script)

import urllib
import json
# noinspection PyUnresolvedReferences
import clr
# noinspection PyUnresolvedReferences
from System.Collections.Generic import Dictionary, List

from pprint import pprint

geoLatEV = "geoLat"
geoLngEV = "geoLng"
geoHashEV = "geoHsh"
limit = 50

googleRegionBias = "us"

global Data, model, q

if model.FromMorningBatch or Data.action == "geocode":
    googleKey = model.Setting("GoogleGeocodeAPIKey", "")


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


    def getPeopleIdsForHash(h):
        qSrc = """
        -- noinspection SqlResolveForFile

        SELECT TOP 100 pp.PeopleId
        FROM (
            SELECT 
            p.PeopleId,
            SUBSTRING(CONVERT(NVARCHAR(18), HASHBYTES('MD2', CONCAT(
                COALESCE(p.AddressLineOne, f.AddressLineOne),
                COALESCE(p.CityName, f.CityName),
                COALESCE(p.StateCode, f.StateCode)
                )), 1), 3, 8) Hash,
            pe.Data as OldHash
            FROM People p 
                LEFT JOIN Families f on p.FamilyId = f.FamilyId
                LEFT JOIN PeopleExtra pe ON pe.Field = '{0}' AND pe.PeopleId = p.PeopleId
            ) pp 
        WHERE pp.Hash = '{1}' AND pp.Hash <> pp.OldHash
        """.format(geoHashEV, h)

        return q.QuerySqlInts(qSrc)


    def doAGeocode():
        # Target List   TODO: remove geocodes for people who have removed their addresses
        qSrc = """
        -- noinspection SqlResolveForFile
        
        SELECT TOP {1} * 
        FROM (
            SELECT 
            p.PeopleId,
            COALESCE(p.AddressLineOne, f.AddressLineOne) Addr1, 
            COALESCE(p.AddressLineTwo, f.AddressLineTwo) Addr2,
            COALESCE(p.CityName, f.CityName) City,
            COALESCE(p.StateCode, f.StateCode) St,
            COALESCE(p.CountryName, f.CountryName) Cn,
            SUBSTRING(CONVERT(NVARCHAR(18), HASHBYTES('MD2', CONCAT(
                COALESCE(p.AddressLineOne, f.AddressLineOne),
                COALESCE(p.CityName, f.CityName),
                COALESCE(p.StateCode, f.StateCode)
                )), 1), 3, 8) Hash,
            pe.Data as OldHash,
            (SELECT COUNT(*) FROM People pi 
                LEFT JOIN Attend at ON pi.PeopleId = at.PeopleId 
                LEFT JOIN Contactees ce ON pi.PeopleId = ce.PeopleId 
                LEFT JOIN Contribution cn ON pi.PeopleId = cn.PeopleId 
                LEFT JOIN OrganizationMembers om ON pi.PeopleId = om.PeopleId 
                WHERE pi.PeopleId = p.PeopleId
                ) Engagement
            FROM People p 
                LEFT JOIN Families f on p.FamilyId = f.FamilyId
                LEFT JOIN PeopleExtra pe ON pe.Field = '{0}' AND pe.PeopleId = p.PeopleId
            ) pp 
        WHERE pp.Addr1 IS NOT NULL AND (pp.Hash <> pp.OldHash OR pp.OldHash IS NULL)
        ORDER BY pp.Engagement Desc
        """.format(geoHashEV, limit)

        i = 0

        setHashes = List[str]()

        for qp in q.QuerySql(qSrc):
            i += 1

            if setHashes.Contains(qp.Hash):
                continue

            setHashes.Add(qp.Hash)

            peopleIds = getPeopleIdsForHash(qp.Hash)
            if not peopleIds.Contains(qp.PeopleId):
                peopleIds.Add(qp.PeopleId)

            p = model.GetPerson(qp.PeopleId)

            country = p.CountryName or ""

            if p.CityName is None and p.ZipCode is None:
                # If able to use Family EVs, switch to use Family here.
                country = p.Family.CountryName or ""

            address = (p.FullAddress + " " + country).strip()

            geo = getGoogleGeocode(address)
            print "<p><b>{}</b></p>".format(geo)

            for pid in peopleIds:
                if geo is None:
                    model.AddExtraValueText(pid, geoHashEV, qp.Hash)
                    model.DeleteExtraValue(pid, geoLatEV)
                    model.DeleteExtraValue(pid, geoLngEV)
                else:
                    model.AddExtraValueText(pid, geoHashEV, qp.Hash)
                    model.AddExtraValueText(pid, geoLatEV, str(geo['lat']))
                    model.AddExtraValueText(pid, geoLngEV, str(geo['lng']))

                print "<p>{}  {}</p>".format(pid, qp.Hash)


    doAGeocode()

elif True:

    mapData = model.DynamicData()
    mapData.cesiumKey = model.Setting("CesiumKey", "")

    mapData.pts = Dictionary[str, Dictionary[str, object]]()
    for p in q.BlueToolbarReport():
        lat = model.ExtraValueText(p.PeopleId, geoLatEV)
        lng = model.ExtraValueText(p.PeopleId, geoLngEV)
        hsh = model.ExtraValueText(p.PeopleId, geoHashEV)

        if lat == "" or lng == "":
            continue

        if not mapData.pts.ContainsKey(hsh):
            mapData.pts.Add(hsh, Dictionary[str, object]({
                'cnt': 0,
                'hash': hsh,
                'families': Dictionary[int, object](),
                'addr': p.AddressLineOne or p.Family.AddressLineOne,
                'lat': lat,
                'lng': lng,
            }))

        if not mapData.pts[hsh]['families'].ContainsKey(p.Family.FamilyId):
            mapData.pts[hsh]['families'][p.Family.FamilyId] = []

        mapData.pts[hsh]['families'][p.Family.FamilyId].Add(p.PeopleId)
        mapData.pts[hsh]['cnt'] += 1

    mapData.ptsl = List[Dictionary[str, object]]()

    for pi in mapData.pts:
        mapData.ptsl.Add(pi.Value)

    template = """

    <script src="https://cesium.com/downloads/cesiumjs/releases/1.79/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.79/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/gh/TenthPres/TouchPointScripts/Mapify/style.min.css" rel="stylesheet">

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

        {{#each ptsl}}
        entities[{{@index}}] = viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees({{this.lng}}, {{this.lat}}, 0),
            name: "{{this.addr}}",
            point: {
                pixelSize: Math.sqrt({{this.cnt}}) * 10,
                color: new Cesium.Color(0, 1, 0, 0.5)
            },
            _data: {
                hash: '{{this.hash}}'
            }
        });
        {{/each}}

        viewer.homeButton.viewModel._command = Cesium.createCommand(flyHome);

        viewer.baseLayerPicker.viewModel.selectedImagery = viewer.baseLayerPicker.viewModel.imageryProviderViewModels[8];

        viewer.infoBox.frame.sandbox = "allow-same-origin allow-top-navigation allow-pointer-lock allow-popups allow-forms allow-scripts";
        viewer.infoBox.viewModel.enableCamera = false;

        // Prevent camera from getting locked to entity via double-click
        viewer.cesiumWidget.screenSpaceEventHandler.setInputAction(function() {}, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

        viewer.scene.skyAtmosphere.show = false;
        viewer.scene.globe.enableLighting = false;
        viewer.scene.globe.showGroundAtmosphere = false;

        new Cesium.FullscreenButton(viewer._toolbar);

        flyHome();

    </script>
    """

    print model.RenderTemplate(template, mapData)
