# Advanced TouchPoint-Mailchimp Sync
Import several Mailchimp lists from separate accounts into TouchPoint and keep them in sync.  

This is different from [TouchPoint's Mailchimp SQL recipes](https://docs.touchpointsoftware.com/EmailTexting/MailChimpIntegration.html) in three primary ways:
1. This will (attempt to) sync both directions.  If someone signs up through Mailchimp, they'll be added to TouchPoint and viceversa.  You therefore do not need to recreate your lists in TouchPoint manually. (Tn fact, it's better for this tool if you don't.)
1. If you have Interests in Mailchimp, they will sync with TouchPoint Sub-Groups. 
1. This allows the lists to be spread across several different lists, and *across several different Mailchimp accounts.*  Thus, if your church has several ministries that all run their own Mailchimp accounts, they can remain separate, and will still stay in sync with TouchPoint. 

While it is possible to enroll new subscribers through the Mailchimp UI, you should prefer to enroll new subscribers through TouchPoint. 

This sync is meant to be run nightly as part of your morning batch.  Note that this means there may be a delay between someone clicking an unsubscribe link, and their unsubscribe request actually being honored.  As long as you run it every day, this delay would be 24 hours or less, which is generally acceptable for CANSPAM purposes.  But, it's something to be aware of nonetheless. 

## Usage

There are two distinct parts of this process: setup and sync. 

### Setup

1.  Load MailchimpSync.py as a special content Python Script. 
1.  In the "lists" array, fill in the username and API keys for each list you want to import.  See the instructions in the comments there for details.
1.  Run the script.  **It will probably take a while to run** and your database will be largely unresponsive while it runs, so maybe don't do this on Sunday morning or during staff office hours. 

## Features That May Be Surprising

- The Import script will save the API Keys to Settings on a per-Mailchimp-account bassis, and will save the Account IDs (numerical) and list IDs (hex) to extra values in the Organization.
- Interest Categories and Interests are imported as Sub-Groups.  **If you use the - character in your Category/Interest/Sub-Group names, you will likely experience unpleasantries.  Avoid this if possible.**


