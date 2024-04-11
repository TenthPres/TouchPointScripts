# API  (Note: this must be the first thing in the script)

import urllib
import json
# noinspection PyUnresolvedReferences
import clr

clr.AddReference('System.Web.Extensions')
# clr.AddReference('System.Collections.Generic')

# noinspection PyUnresolvedReferences
from System.Web.Script.Serialization import JavaScriptSerializer

# noinspection PyUnresolvedReferences
from System.Collections.Generic import Dictionary, List

xhrLimit = 500

googleRegionBias = "us"

global Data, model, q

model.Title = "Mapify"

if model.Data.p == "" and model.Data.fams == "":  # Blue Toolbar Page load

    mapData = model.DynamicData()
    mapData.cesiumKey = model.Setting("CesiumKey", "")
    mapData.xhrLimit = xhrLimit
    mapData.count = q.BlueToolbarCount()

    template = """

    <script src="https://cesium.com/downloads/cesiumjs/releases/1.116/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.116/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/gh/TenthPres/TouchPointScripts/Mapify/style.min.css" rel="stylesheet">

    <div id="cesiumContainer" class="fullSize"></div>
    <div id="loadingOverlay"><h2>Loading...</h2></div>
    <div id="toolbar"></div>
    <div id="statusInfo" title="People who aren't shown probably could not be located on the map.">
        Showing <span id="showingCount">0</span> of {{count}} people
    </div>

    <script>
    Cesium.Ion.defaultAccessToken = '{{{cesiumKey}}}';
    const viewer = new Cesium.Viewer('cesiumContainer', {
            animation : false,
            fullscreenButton: false, // will be manually created later in the toolbar
            geocoder : false,
            infoBox: true,
            skyAtmosphere: false,
            skyBox: false,
            timeline : false,
            scene: {
                fog: {
                    enabled: false
                },
                globe: {
                    enableLighting: false,
                    showGroundAtmosphere: false
                }
            }
        });

    var flyHome = function() {
        viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(-75.169899, 39.947262, 85000.0), // TODO replace with church lat/lng setting
            duration: 4
        });
    };

    function clearInfobox() {
        viewer.infoBox.frame.contentDocument.body.removeChild(viewer.infoBox.frame.contentDocument.body.firstChild)
        viewer.infoBox.frame.removeEventListener('load', clearInfobox);
    }

    viewer.homeButton.viewModel._command = Cesium.createCommand(flyHome);
    viewer.baseLayerPicker.viewModel.selectedImagery = viewer.baseLayerPicker.viewModel.imageryProviderViewModels[8];
    viewer.infoBox.frame.sandbox = "allow-same-origin allow-top-navigation allow-pointer-lock allow-popups allow-forms allow-scripts";
    viewer.infoBox.frame.src = "/HomeWidgets/Embed/0";
    viewer.infoBox.frame.addEventListener('load', clearInfobox);
    viewer.infoBox.viewModel.enableCamera = false;
    viewer.scene.globe.showGroundAtmosphere = false;

    // Prevent camera from getting locked to entity via double-click
    viewer.cesiumWidget.screenSpaceEventHandler.setInputAction(function() {}, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

    // Handle Entity Selection
    viewer.cesiumWidget.screenSpaceEventHandler.setInputAction(function(movement) {
        var clickedOn = viewer.scene.pick(movement.position),
            clickedEntity = (Cesium.defined(clickedOn)) ? clickedOn.id : undefined;
        if (Cesium.defined(clickedEntity)) {
            viewer.selectedEntity = handleSelectedEntity(clickedEntity);
        } else {
            viewer.selectedEntity = undefined;
        }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    new Cesium.FullscreenButton(viewer._toolbar);

    let entities = {},
        showCount = 0,
        requestsNeeded = Math.ceil({{{count}}} / {{{xhrLimit}}}),
        colorAssignments = {},
        categoricalColors = [
            new Cesium.Color(0, 1, 0, 0.5),
            new Cesium.Color(1, 0, 0, 0.5),
            new Cesium.Color(0, 0, 1, 0.5),
            new Cesium.Color(1, 1, 0, 0.5),
            new Cesium.Color(0, 1, 1, 0.5),
            new Cesium.Color(1, 0, 1, 0.5),
            new Cesium.Color(0, .4, 0, .5)
        ],
        nullColor = new Cesium.Color(0, 0, 0, 0.5);

    function reqListener() {
        let start = this.responseText.indexOf(">>DATA>") + 7,
            data = JSON.parse(this.responseText.substr(start, this.responseText.indexOf("<DATA<<") - start))

        for (const hsh in data) {
            if (!entities.hasOwnProperty(hsh)) {
                entities[hsh] = viewer.entities.add({
                    position: Cesium.Cartesian3.fromDegrees(data[hsh].lng, data[hsh].lat, 0),
                    name: data[hsh].addr,
                    point: {
                        pixelSize: Math.sqrt(data[hsh].cnt) * 10,
                        color: nullColor
                    },
                    _data: {
                        loaded: false,
                        hash: hsh,
                        famIds: data[hsh].families,
                        resCode: data[hsh].resCode
                    }
                });
                entities[hsh].point.color = computeColor(entities[hsh]);
                showCount += data[hsh].cnt;
            } else {
                console.warn("ERROR: hash points need to be merged across requests."); // TODO
            }
        }

        // Update count of number of people shown
        document.getElementById("showingCount").innerHTML = "" + showCount;

        // Fully Loaded
        requestsNeeded--
        if (requestsNeeded <= 0) {
            flyHome();
            document.getElementById('loadingOverlay').style.opacity = 0;
        }

    }

    for (var r = 1; r <= requestsNeeded; r++) {
        let url = window.location.origin + window.location.pathname + "?p=" + r,
            xhr = new XMLHttpRequest();
        xhr.addEventListener("load", reqListener);
        xhr.open("GET", url);
        xhr.send();
    }

    function colorForCategory(field, category) {
        if (!colorAssignments.hasOwnProperty(field)) {
            colorAssignments[field] = {
                values: {},
                count: 0
            }
        }
        if (!colorAssignments[field].values.hasOwnProperty(category)) {
            let index = colorAssignments[field].count % categoricalColors.length;
            colorAssignments[field].values[category] = categoricalColors[index];
            colorAssignments[field].count++;
        }
        return colorAssignments[field].values[category];
    }

    function computeColor(entity) {
        colorBasis = "resCode";

        if (["resCode"].indexOf(colorBasis) > -1) {  // categorical fields
            return colorForCategory(colorBasis, entity._data[colorBasis]);
        } else {  // quantified fields
            console.warn("Quantified colors not yet available")
        }
    }

    function handleSelectedEntity(selectedEntity) {
        if (selectedEntity._data.loaded === false) {
            let url = window.location.origin + getPyScriptAddress(),
                xhr = new XMLHttpRequest();
            selectedEntity._data.loaded = undefined; // loading
            selectedEntity.description = "loading...";
            xhr.addEventListener("load", function() {
                updateEntityWithPersonalData(selectedEntity, this);
            });
            xhr.open("POST", url, true);
            xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            xhr.send("hsh=" + selectedEntity._data.hash + "&fams=" + JSON.stringify(selectedEntity._data.famIds));
        } else {
            correctIframeHeight();
        }

        return selectedEntity;
    }

    function getPyScriptAddress() {
        let path = window.location.pathname;
        path = "/PyScriptForm/" + path.substr(18, path.length - 54);

        return path;
    }

    function updateEntityWithPersonalData(entity, xhrResp) {
        let start = xhrResp.responseText.indexOf(">>DATA>") + 7,
            data = xhrResp.responseText.substr(start, xhrResp.responseText.indexOf("<DATA<<") - start)

        entity._data.loaded = true;
        entity.description = data;

        correctIframeHeight();
    }

    function correctIframeHeight() {
        let iframe = viewer.infoBox.frame;
        setTimeout(() => {
            iframe.style.height = parseFloat(iframe.style.height.split('p')[0]) + 20 + "px";
        }, 50);
    }

    function imageLoaded(that) {
        that.parentElement.style.backgroundImage = "url(" + that.src + ")";
        that.parentElement.style.opacity = 1;
    }

    </script>
    """

    print model.RenderTemplate(template, mapData)


elif model.Data.p != "":  # XHR Map Data Request

    model.Data.p = int(model.Data.p)

    geoSql = "SELECT g.id geoId, g.Latitude lat, g.Longitude lng FROM People p LEFT JOIN Geocodes g ON g.Address = CONCAT(p.PrimaryAddress, ' ', p.PrimaryAddress2, ' ', p.PrimaryCity, ' ', p.PrimaryState , ' ', p.PrimaryZip) WHERE p.PeopleId = {}"

    pts = Dictionary[str, Dictionary[str, object]]()
    for p in q.BlueToolbarReport(None, xhrLimit, xhrLimit * (model.Data.p - 1)):
        geo = q.QuerySqlTop1(geoSql.format(p.PeopleId))

        lat = geo.lat
        lng = geo.lng
        hsh = "{}|{}".format(geo.lat, geo.lng)

        if lat == "" or lng == "":
            continue

        if not pts.ContainsKey(hsh):
            resCode = p.ResidentCode or p.Family.ResidentCode
            if resCode is not None:
                resCode = resCode.Code

            pts.Add(hsh, Dictionary[str, object]({
                'cnt': 0,
                'hash': hsh,
                'families': Dictionary[str, object](),
                'addr': p.AddressLineOne or p.Family.AddressLineOne,
                'lat': lat,
                'lng': lng,
                'resCode': resCode
            }))

        if not pts[hsh]['families'].ContainsKey(str(p.Family.FamilyId)):
            pts[hsh]['families'][str(p.Family.FamilyId)] = []

        pts[hsh]['families'][str(p.Family.FamilyId)].Add(p.PeopleId)
        pts[hsh]['cnt'] += 1

    print "<!-- >>>>>DATA>" + JavaScriptSerializer().Serialize(pts) + "<DATA<<<<< -->"


elif model.HttpMethod == 'post' and model.Data.fams != '' and model.Data.hsh != '':  # XHR Point data request
    included = JavaScriptSerializer().DeserializeObject(model.Data.fams)
    includedPeop = []
    for f in included.Values:
        for p in f:
            includedPeop.append(p)
    includedFams = JavaScriptSerializer().Serialize(included.Keys).replace('"', '')[1:-1]
    includedPeop = JavaScriptSerializer().Serialize(includedPeop).replace('"', '')[1:-1]

    sql = """
    -- noinspection SqlResolveForFile

    SELECT *, 1 as [includedFamily], (IIF(p.PeopleId IN ({3}), 1, 0)) as [includedPerson]
        FROM People p
            LEFT JOIN Families f on p.FamilyId = f.FamilyId
            LEFT JOIN PeopleExtra pe ON pe.Field = '{0}' AND pe.PeopleId = p.PeopleId
    WHERE p.FamilyId IN ({2})
    UNION
    SELECT *, 0 as [includedFamily], (IIF(p.PeopleId IN ({3}), 1, 0)) as [includedPerson]
        FROM People p
            LEFT JOIN Families f on p.FamilyId = f.FamilyId
            LEFT JOIN PeopleExtra pe ON pe.Field = '{0}' AND pe.PeopleId = p.PeopleId
    WHERE pe.Data = '{1}' AND p.FamilyId NOT IN ({2})
    ORDER BY includedFamily DESC, p.FamilyId ASC, includedPerson DESC, p.PositionInFamilyId
    """.format("null", model.Data.hsh, includedFams, includedPeop)

    famId = 0
    out = '''
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/gh/TenthPres/TouchPointScripts/Mapify/style-infobox.min.css" rel="stylesheet">
    '''

    template = """
    {{IfNotEqual d.FamilyId d.PrevFamilyId}}
        {{IfGt d.PrevFamilyId 0}}
            </div></div>
        {{/IfGt}}
    <div class="family{{IfEqual d.includedFamily 1}} included{{else}} excluded{{/IfEqual}}">
        <h2>
        The {{ p.Family.HeadOfHousehold.Name }} Family
        {{IfNotEqual d.HomePhone ''}}
            <a href="tel:{{d.HomePhone}}" class="fa fa-phone" title="Call Home Phone"></a>
        {{/IfNotEqual}}
        </h2><div class="family-members">
    {{/IfNotEqual}}

    <div class="person{{IfEqual d.includedPerson 1}} included{{else}} excluded{{/IfEqual}}">
        <div class="person-photo"
            {{IfNotEqual pHasPhoto 0}}
            style="background-position: {{p.Picture.X}}% {{p.Picture.Y}}%; opacity:0;">
            <img onload="parent.imageLoaded(this)" src="/Portrait/{{ p.Picture.SmallId }}"
            /{{/IfNotEqual}}>
        </div>
        <h3>
            <a href="/Person2/{{d.PeopleId}}" target="_blank">{{d.Name}}</a>
        </h3>
        {{IfNotEqual d.includedPerson 1}}<p class="note">(not included in search)</p>{{/IfNotEqual}}
        <p>
            {{IfNotEqual d.EmailAddress ''}}
                <a href="mailto:{{d.EmailAddress}}" class="fa fa-envelope" title="Send Email"></a>
            {{/IfNotEqual}}
            {{IfNotEqual d.CellPhone ''}}
                <a href="tel:{{d.CellPhone}}" class="fa fa-mobile" title="Call Mobile Phone"></a>
            {{/IfNotEqual}}
            {{IfNotEqual d.WorkPhone ''}}
                <a href="tel:{{d.WorkPhone}}" class="fa fa-phone" title="Call Work Phone"></a>
            {{/IfNotEqual}}
        </p>
    </div>
    """

    for Data.d in q.QuerySql(sql):
        Data.d.PrevFamilyId = famId
        Data.p = model.GetPerson(Data.d.PeopleId)
        Data.pHasPhoto = 1 * (Data.p.Picture is not None)

        out += model.RenderTemplate(template)

        famId = Data.d.FamilyId

    out += "</div></div>"

    print "<!-- >>>>>DATA>" + out + "<DATA<<<<< -->"