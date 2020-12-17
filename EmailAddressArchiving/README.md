# Email Address Archiving

This script puts all email addresses associated with a Person record into a JSON array, stored as an extra value. This
Allows one person record to have more than two email addresses associated with the record.  Also, depending on how 
your permissions are configured for this Extra Value, you can functionally make these indellible.  

Since many email addresses are permanently associated with a Person, this reduces the liklihood of creating duplicates
when importing data from other separate systems.  See our Mailchimp and ConstantContact integrations for examples.

This script is intended to be included in the nightly batch routine. 

This will also combine and clean up email addresses from record merges, **so long as the script is able to run both 
before and after the merge**.

## IMPORTANT

Until [PR 1205](https://github.com/bvcms/bvcms/pull/1205) is merged and published, this will only work for the first 
1000 people records in your database. 