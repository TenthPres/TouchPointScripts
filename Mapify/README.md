# Mapify

**THIS PROJECT IS NOT READY FOR DISTRIBUTION.** Contributions welcome, but please do not install this in your 
database yet unless you really know what you're doing. 

![Mapify Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/MapifyScreenshot.png?raw=true)

## Aspirations

Wondering which neighborhoods need a new Small Groups?  Or where your attendees actually come from?  See 
people from any search (or org or any other scenario with a Blue Toolbar) on a highly-interactive globe of the 
world.

The globe is provided by Cesium, a really awesome geospatial visualization tool, because it handles large and 
dynamic datasets better than Google Maps.  Each unique address will be represented by a dot on the map, and the
size of the dot is proportional to the number of people within the set at that address. 

To make this work well at scale, **all records in your database will be geocoded**.  This process will happen
gradually, probably over a few days.  Your maps won't be very exciting until that process is complete. 

## Installation
1.  You will need a free Access Token from [Cesium Ion](https://cesium.com/ion/tokens).  Save it as a setting with 
    the name "CesiumKey".  
1.  You will need at least one geocoding API Key.  This library uses Bing by default, and falls back to Google. (Bing
    has a higher limit on its free tier.) You will have the best results if you use both. 
1.  Download the zip file from the releases and install it at `mychurch.tpsdb.com/InstallPyScriptProject`.  This will 
    install the script, and add the geocoding task to your morning batch.  The geocoding task will work through your 
    database 5000 records per day, prioritizing those who have been active-ish recently.
1.  After most of your active-ish folk have been geocoded, the report will automatically be added to your custom reports 
    menu in the Blue Toolbar.  By default, it will be accessible to anyone with the Access role.  You can change this 
    by changing your custom report settings. 


## To-Do
- Report the number of records not shown. 
- Improve background/morning geocoding
- Get >1000 results.  (Probably requires PR to TouchPoint.) 
    - Sort by extra value?
- Move script to CDN. 
- Separate data-loading into separate API call, if possible. (Likely to requrie a PR to TouchPoint.)
- Give infobox useful content.  Load separately from main request. 
- Make colors dynamic from a collection of standard fields.


### Maybe someday
- Find people using geocoder search
- Custom coloring criteria
