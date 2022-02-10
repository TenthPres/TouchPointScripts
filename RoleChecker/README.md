# Role Checker

**NOTE: Unlike most of the scripts in this repository, this will require significant customization before it can be 
adapted for other churches.**

This script, run as part of our Morning Batch, make sure the right people have the right permissions. While this does 
not handle all permissions, it does handle many of the most common ones, especially for lay leaders.  

Members of Session, the Diaconate, Staff, and the Women's Committee (which provides a sort of pastoral care for women) 
all have "Access".  Leaders of involvements like Small Groups and Bible School classes who are not part of the 
aforementioned involvements also have the OrgLeadersOnly restriction. 

As an example, our small groups manage their own rosters, including adding and removing co-leaders.  With this script 
running every morning, new leaders are able to manage their groups without intervention from the staff admins.

## Installation

At a minimum, to use this for your church, you will need to adjust the Org IDs and the leader types. 

We have this in a script separate from the MorningBatch, which enables us to call it manually sometimes (e.g. when we 
add a new class of Elders) and then have `model.CallScript('RoleChecker')` in our MorningBatch for automatic updates.
