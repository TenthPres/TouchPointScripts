# Mapify

**THIS PROJECT IS NOT READY FOR DISTRIBUTION.** Contributions welcome, but there are a couple key features that
aren't *quite* feasible yet.  

![Mapify Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/MapifyScreenshot.png?raw=true)

Wondering which neighborhoods need a new Small Group?  Or where your attendees actually come from?  See 
people from any search (or org or any other scenario with a Blue Toolbar) on a highly-interactive globe of the 
world.

## Features

This script does two things:
1. Geocode the addresses of people who have them, and
1. Display results of a search (or Involvement or anything with a Blue Toolbar) on a highly-interactive and engaging 
   map.

## Details
The globe is provided by Cesium, a really awesome geospatial visualization tool, because it handles large and 
dynamic datasets better than Google Maps.  Each unique address will be represented by a dot on the map, and the
size of the dot is proportional to the number of people within the set at that address. 

To make this work well at scale, **all records in your database will be geocoded** and saved to Extra Values on each 
person's record.  This process will happen gradually, probably over a few days.  Your maps won't be very exciting until 
that process is complete. 

## Installation
1.  You will need a free Access Token from [Cesium Ion](https://cesium.com/ion/tokens).  Save it as a setting with 
    the name "CesiumKey".  
1.  You will need a Google Geocoding API Key saved to a setting called "GoogleGeocodeAPIKey".  This is the same setting 
    used for TouchPoint's built-in Small Group Finder.  You can find [instructions for creating an API Key in the 
    TouchPoint documentation.](https://docs.touchpointsoftware.com/Organizations/SmallGroupFinderMap.html)
1.  Download the Mapify zip file from the releases and install it at `mychurch.tpsdb.com/InstallPyScriptProject`.  This 
    will install the script, and add the geocoding task to your morning batch.  The geocoding task will work through 
    your database around 1000 records per day, prioritizing those who have been active-ish recently.  This should keep
    geocoding costs within Google's free tier.  It will also add the report to your Blue Toolbar menu.
1.  Optional: You may want to add the geocoding Extra Values as Standard Extra Values to prevent users from errantly 
    modifying them.  The three Extra Value names used by default are `geoLat`,`geoLng`, and `geoHsh` and all use the 
    type "Text (single line)".  At Tenth, we have them restricted to the Developer role, because none of our users 
    really need this.  You can still query them in SQL without direct access, if you're into that.

The 'Mapify' report probably won't be very useful until after a few days of geocoding.  You can check how many people 
have been geocoded by creating a Search (Builder) searching for people who have an "Extra Value Text" Not Equal to "" 
(blank) with the name "GeoLat"

## To-Do
- Report the number of records not shown.  (Pending PR to TouchPoint.)
- Get >1000 results.  (Pending PR to TouchPoint.)
- Move script to CDN.
- Make colors dynamic from a collection of standard fields.

### Maybe someday
- Find people using geocoder search field
- Custom coloring criteria
