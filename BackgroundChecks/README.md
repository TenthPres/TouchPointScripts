# Background Check Automation

This script provides a full process for managing background checks in the specific and strange ways Pennsylvania requires,
and then goes a bit above and beyond. 

As currently configured, this runs/looks for checks on the following schedule:
- Minors do not need background checks.  They are listed to get actual background checks at 17 and 9 months.
- PATCH is run once every five years (as required by law).  This system does not have a means for checks to be imported. 
Therefore, if a volunteer already has this check, it will need to be run again through ProtectMyMinistry.
- CAHC is run once every five years (as required by law).  This system does not have a means for checks to be imported. 
Therefore, if a volunteer already has this check, it will need to be run again through ProtectMyMinistry.
- FBI Fingerprinting is required every five years for someone who has lived outside PA within the last ten years.  This 
is a manual process that can't be automated much.  However, this tracks that process and provides reminders when renewals
are due.
- Alternatively to the FBI Fingerprinting, volunteers who have lived within PA for the last 10 years can e-sign an 
affidavit stating that they have lived in PA for that duration.  This process uses Adobe Sign (subscription required).
