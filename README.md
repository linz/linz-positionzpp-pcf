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
    "ReferenceFrame": "ITRF2008",
    "OutputStatusFile": "OUT/STATUS.LCK",
    "OutputSummaryJson": "OUT/SUMMARY.JSON",
    "ConfigOutputFiles": [
        {
            "source": "output_files/readme.txt",
            "target": "readme.txt",
            "description": "Information about these results"
        }
    ],
    "CampaignOutputFiles": [
        {
            "source": "SOL/MIN{session}.SNX",
            "target": "min_{jobcode}_{subjobid}.snx",
            "description": "SINEX file of minimum constraints calculation for {origcodes} ({origfiles})"
        },
        {
            "source": "SOL/FIN{session}.SNX",
            "target": "fin_{jobcode}_{subjobid}.snx",
            "description": "SINEX file of final coordinate calculation for {origcodes} ({origfiles})"
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
files | the user's RINEX files used after renaming
origfiles | the user's RINEX files used
codes | the user's mark codes after renaming
origcodes | the original user's make names

ConfigOutputFiles are files sourced relative to this configuration file.
CampaignOutputFiles are copied for each Bernese campaign run by the job and are sourced relative to the Bernese campaign directory.
