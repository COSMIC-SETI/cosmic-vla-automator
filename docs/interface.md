# Interfacing requirements for the automator

## Redis status keys:

The keys are under the `Automator` hash.

These keys should be set as close to the originating source as possible. E.g. 
in the case of the VLA, `mcast2redis.py` should set some of these directly 
upon receiving a metadata packet.  

These keys are expected to be updated the instant they change. There is no 
need for timestamps as Redis provides this already. 

1. **Current fengine status:**  
**key:** `fengine_status`  
**value:** JSON dict containing `{<antenna>:<status>}`  
**status:** can be `enabled`, `disabled`, `error`

2. **Current recording mode:**  
**key:** `<host/instance>:rec_mode`  
**value:** string containing recording mode  
**status:** can be `voltage` or `correlator` 

3. **Recording output directories:**  
**key:** `<host/instance>:rec_dir`  
**value:** File path to current directory in which raw files will be written

4. **Current recording status:**  
**key:** `<host/instance>:rec_status`  
**value:** Recording status  
**status:** can be `recording`, `idle`, `error`, `armed`

5. **Current processing status:**  
**key:** `<host/instance>:proc_status`  
**value:** Processing status  
**status:** can be `processing`, `idle`, `error`, `pending`

6. **Processing output directory**  
**key:** `<host/instance>:proc_dir`  
**value:** Upper directory in which processing data products are currently being  written

### These below pretty much exist already

7. **Current antenna tracking status:**  [already exists]  
**key:** `on_source_antennas`  
**value:** List of on source antennas

8. **Source name:** [already exists]  
**key:** `src_name`  
**value:** Current primary source

9. **Primary RA:** [already exists]  
**key:** `ra`  
**value:** Current primary right-ascension in degrees

10. **Primary Dec:** [already exists]  
**key:** `dec`  
**value:** Current primary declination in degrees






