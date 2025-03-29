# tidalauth

**WIP - not working - gets the IP blocked**

Companion project to https://github.com/dorskfr/tidalidarr

Meant to be run as a cronjob or in a loop, checks your tidalidarr URL /auth endpoint to see if necessary to login.

If so, accesses the device authorization link and validates.

This saves having to monitor if the token is expired and needs to be approved again every 7 days.
