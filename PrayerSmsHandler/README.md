# Prayer SMS Handler

This is a relatively simple script that receives text messages and immediately saves them as Notes on the sender's profile. 

The design makes a few assumptions:
- You have a phone number that you use ONLY for this purpose, and it is already connected to TouchPount.  Hypothetically, you
can use MBT or Twilio.  We use Twilio. 
- You aren't using any Reply Words for this number/group.
- You're comfortable with the possibility that a prayer request will be assigned to the wrong person if a phone number is 
saved on multiple people's profiles. 

## Setup
1. Copy the contents of PrayerSmsHander.py to your TouchPoint Python special content.  You can call this file whatever you 
want, but you'll need to use that name where we use PrayerSmsHandler below.
2. In the python script, edit the section under Variables to Update.  You'll need to provide:
   - The PeopleId of a generic person who will be associated with the requests coming from unknown users
   - The PeopleId of someone who will clean up the data when an unknown user submits a request and later submits their name
   - The ID numbers of the keywords you wish to use.  To find these keywords, run the following in a separate SQL Special Content:
       ```
       SELECT KeywordId as ID, Description FROM Keyword WHERE IsActive = 1
       ```
3. Configure the SMS Reply Word for this group with a special default. The Reply Word should be blank, the action should be "Run
    Python Script", and the Script Name should be the name of the script you created in step 1.  (For us, "PrayerSmsHandler")  Everything 
    other than the Action and Script Name should be blank.
    ![Mapify Screenshot](https://github.com/TenthPres/TouchPointScripts/blob/master/.documentation/PrayerSmsReplyWord.png?raw=true)
