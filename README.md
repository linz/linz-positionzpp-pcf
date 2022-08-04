# linz-positionz-pcf

This contains the Bernese PCF and configuration scripts for running a PositioNZ-PP job.

When PositioNZ-PP processes a job it clones this repository using a specific branch/tag.
By default the tag "pnzpp-prod" is used for processing in the production environment, and
"pnzpp-nonprod" for processing in the nonprod environment.

This contains the following directories:

* config: contains the configuration information used by the processing script in config.json.  Also may contain a template for files that will be installed into the campaign directory before the processing is run.
* user: contains the Bernese USER directory files defining the processing strategy
* bernese: contains files that will be installed into the Bernese system GPS directory before the processing is run.

The structure of the configuration file (config/config.json) is as follows:

```json
{
    "PcfName": "RUN_PNZ",
    "ItrfCoordsys": "ITRF2008",
    "OutputStatusFile": "STATUS.LCK",
    "OutputSummaryJson": "SUMMARY.JSON",
    "SaveFiles": [
        {
            "source": "SOL/MIN{session}.SNX",
            "target": "min_{subjobcode}_{subjobid}.snx"
        },
        {
            "source": "SOL/FIN{session}.SNX",
            "target": "fin_{subjobcode}_{subjobid}.snx"
        }
    ]
}
```

The configuration items in this file and the files in the config/campaign template may include strings {_varname_} which are replaced as follows:

varname | value
--- | ---
subjobcode | A code for the Bernese job based on the station code in the user RINEX file
subjobid | A numeric id for the subjob starting at 1
session | the bernese session id of the job
YYYY | The 4 digit year of the job
YY | The 2 digit year of the job
DDD | the day of year of the session
DD | the day of month of the session
MM | the month number of the session
MMM | the 3 character month of year (eg JAN)
hh | the hour of the middle of the processing session
mm | the minute of the middle of the processing session
ss | the second of the middle of the processing session
