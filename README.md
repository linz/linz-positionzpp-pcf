# linz-positionz-pcf

This contains the Bernese PCF and configuration scripts for running a PositioNZ-PP job.

When PositioNZ-PP processes a job it uses this repository for configuration.
The protected branch "pnzpp-prod" is used for processing in the production environment, and the branch
"pnzpp-nonprod" for processing in the nonprod environment.

This contains the following directories:

* config: contains the configuration information used by the processing script in config.json.  Also may contain a template for files that will be installed into the campaign directory before the processing is run in config/campaign_template
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
    ],
    "ReferenceDataFiles": {
        "AntennaFile": "PCV_COD.I08",
        "ReceiverFile": "RECEIVER.",
        "ExtraReceiverConfigFile": "config/RECEIVER.MISSING",
        "CombinedReceiverFile": "RECEIVER.ALL"
    }
}
```

The configuration items in this file and the files in the config/campaign_template may include strings {_varname_} which are replaced as follows:

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

ReferenceDataFiles are used when the Bernese reference data (mainly GPS/GEN contents) are updated by the daily sync-config task.  This includes the option of adding extra receivers to the Bernese receivers file using a file of receivers in this configuration.  The AntennaFile and CombinedReceiverFile (or ReceiverFile if it is not defined) are used to compile the list of valid antennae and receivers used by the front end GUI.  The AntennaFile value may be a list of files used to compile the full set of antennae, eg 

```json
"AntennaFile": ["I14.ATX","NGS14.ATX"]
```

