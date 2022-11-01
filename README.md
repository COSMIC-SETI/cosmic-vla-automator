# cosmic-vla-automator

Automation for commensal observing with COSMIC at the VLA. The `automator` process is designed to enable commensal observing and SETI search to take place without human intervention.   

At least two modes of operation are required: standard "stop and stare" observing and VLASS-style scanning observations. 

Planning for VLASS observations is available here: [commensal observing with VLASS](docs/vlass-automation.md)

### Interacting manually via the command line:  
  
Many of the functions of the automator can be used manually via 
the commandline with the interface module. To use, make sure you 
are in the `cosmic_vla` virtual environment:

```
conda activate cosmic_vla
```

Then, the following commands are available:

```
python3 interface.py 

Select a command from the following:

    record_fixed         Record a fixed RA/Dec. Requires args:
                             duration:  time to record in seconds

    stop_record          Stop current in-progress recording.

    telescope_state      Current state of the telescope

    fengine_state        Aggregate F-engine state

    expected_antennas    List of antennas which should be active

    daq_states           DAQ statuses. Requires args:
                             domain:    hashpipe domain
                             instances: hashpipe instances

    daq_receive_state    Status of DAQ receiving. Requires args:
                             domain:   hashpipe domain
                             instance: hashpipe instance

    daq_record_state     Status of DAQ recording. Requires args:
                             domain:   hashpipe domain
                             instance: hashpipe instance

    datadirs             Retrieve DATADIR. Requires args:
                             domain:    hashpipe domain
                             instances: hashpipe instances

    outputdirs           Location of recorded output data. Requires args:
                             domain:    hashpipe domain
                             instances: hashpipe instances

    daq_record_modes     Recording mode for DAQ instances. Requires args:
                             domain:    hashpipe domain
                             instances: hashpipe instances

    src_name             Current source name
