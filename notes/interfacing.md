### Interfacing requirements: standard observation 

1. Observing state: waiting
    - Detect that a standard observation is imminent
    - Knows when backends and ancillary processes are ready to record

2. Observing state: recording
    - Knows:
        - When a primary source is being tracked (fixed RA and Dec)
        - When incoming data from all antennas and F-engines 
        is trustworthy
        - If at any time data from all antennas and F-engines ceases
        to be trustworthy
        - If at any time a primary source ceases to be tracked
    - Instructs backends to record
    - Requests targets in field of view surrounding the primary source
    - Notes on target selector:
        - Knowledge of prior observations via local replicated BLDW tables
        - Uses this to determine observing priority
        - Delivers targets to backends/recipe file generator

3. Observing state: processing
    - Knows: 
        - When backends have completed recording
        - Associated metadata
    - Initiates processing pipeline and any intermediate steps if required
    - Delivers any metadata still required
    - Inhibits recording during this time

4. Observing state: processing completed
    - Knows: 
        - When processing has been completed
        - Processing success (by node, stage, etc)
    - Instructs that NVMe drives be cleared
    - Returns to waiting state. 

Important: 
If a primary source ceases to be tracked at any time, OR the incoming data
ceases to be trustworthy, recording is stopped and processing takes place.  

### Interfacing requirements: VLASS


### CLI requirements

- DWELL or equivalent
- Processing parameters: 
    - Which pipeline
    - Hyperparameters
- Thresholds for trusting incoming data (node count, antenna count)
- Thresholds for initiating or aborting processing (Tobs < DWELL, etc)