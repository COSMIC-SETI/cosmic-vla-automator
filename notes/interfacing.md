### Interfacing requirements: standard observation 

1. Observing state: waiting
- Detect that a standard observation is imminent
- Instructs backends and ancillary processes to prepare
- Delivers appropriate metadata if needed
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

1. Observing state: waiting
- Detects that a VLASS observation is imminent
- Instructs backends and ancillary processes to prepare
- Delivers appropriate metadata if needed
- If necessary: would instruct target selector to preselect a strip
of sky for upcoming high-cadence target delivery
- Knows when backends and ancillary processes are ready to record

2. Observing state: record-process
- Assumption that the 10s record-process-repeat cycle will be automated
at a low level, more akin to a reflex arc. This can be automated here if
need be, but prior discussions suggest at least some of this should take
place at a lower level. 
- Instructs backends and ancillary processes to initiate the 
record-process cycle for as long as a VLASS track is running. 
- Simultaneously instructs the target selector to begin calculating and
delivering targets at the midpoint of each 10s strip
- Question: should this be reactive or follow pre-calculated midpoints?

3. Observing state: end-of-strip
- Recording and processing should not take place while slewing to the
beginning of the next track
- Once this is complete, return to state 2. 

4. Observing state: processing completed
- Returns to state 1.

As above, if a primary source ceases to be tracked at any time, OR the incoming data
ceases to be trustworthy, recording is stopped and processing takes place.  

### CLI requirements

- DWELL or equivalent
- Processing parameters: 
    - Which pipeline
    - Hyperparameters
- Thresholds for trusting incoming data (node count, antenna count)
- Thresholds for initiating or aborting processing (Tobs < DWELL, etc)