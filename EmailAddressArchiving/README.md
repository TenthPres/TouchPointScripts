# Email Address Archiving

If you import people from other systems (like our Mailchimp and Constant Contact integrations), this tool helps 
prevent the creation of duplicates by allowing more than two email addresses to be associated with an account. 

## Rationale

Jake Hypothetical has been connected with the church for a few years.  Through that time, he graduated from college,
became a member of the church, and now works in the area.  He joined the College email list with his University email 
address, he became a member with his personal email address, and at some point he put his work email address into a
form.  TouchPoint can only have two email addresses associated with a person.  So Jake's three addresses are hard to
store. 

When we sync the college email list from Mailchimp, this tool gives us a chance of not creating duplicate entries. Or,
at least, not creating re-creating duplicates after the first duplicates are merged. 

## How it Works (conceptually)

This script puts all email addresses associated with a Person record into a JSON array, stored as an extra value. This
allows one person record to have more than two email addresses associated with the record.  

When the import tools run (at least, our inport tools), not only will the search look for matching records based on 
the normal email fields, but also this extra value. 

This script is intended to be included in the morning batch routine. 

### Merging

This will also combine and clean up email addresses from record merges, **so long as the script is able to run both 
before and after the merge**.  That means, after you merge, don't merge that merged profile again.

## Immutability

You, as the admin of your church's TouchPoint database, can make these lists functionally immutable.  To do this, make
`EmailAddresses` a Standard Extra Value, limited to the Admin role (or the API role, or some other uncommon role).

## Caution

This script will take several seconds or a few minutes to run, especially the first few times.  During this time, 
TouchPoint may be unresponsive for all users.  Therefore, we strongly encourage running this only as part of the 
morning batch.

## How to Install

### Option 1: Install Automatically with a Sync Tool
1.  Install [our Mailchimp Sync tool](../mailchimp) or [our ConstantContact Sync tool](../constantcontact).  This tool
    is installed automatically. 

### Option 2: Install Manually
1.  In the Special Content section, create a new Python Script called `EmailAddressArchiving`.
1.  Paste into that script all of the content from [EmailAddressArchiving.py](EmailAddressArchiving.py)
1.  If you don't already have a morning batch script:
    1.  Create a new python script called `MorningBatch`. 
        ([Read more here.](https://docs.touchpointsoftware.com/Administration/MorningBatch.html))
    1.  From `Administration > Setup > Settings`, change the setting `RunMorningBatch` to `True`
1.  Add `model.CallScript('EmailAddressArchiving')` to your Morning Batch script.
