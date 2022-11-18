# Interfacing requirements for the automator

## Redis status keys:

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
**status:** [What possibilities currently exist? See request in Slack] 

3. **Recording output directories:**  
**key:** `<host/instance>:rec_dir`  
**value:** File path to current directory in which raw files will be written

4. **Current processing status**  
**key:** `<host/instance>:proc_stat`  
**value:** Current status of processing  
**status:** `processing`, `idle`, `error`

6. **Processing output directory**  
**key:** `<host/instance>:proc_dir`  
**value:** Upper directory in which processing data products are currently being 
written    

7. **Current recording status:**  
**key:** `<host/instance>:rec_status`  
**value:** Recording status
**status:** can be `recording`, `idle`, `error`, `armed`

8. **Current processing status:**  
**key:** `<host/instance>:proc_status`  
**value:** Processing status
**status:** can be `processing`, `idle`, `error`, `pending`

9. **Required antennas:** 
**key:** `required_antennas`  
**value:** List of antennas required for current observation.

### These below pretty much exist already

10. **Current antenna tracking status:**  [already exists pretty much]
**key:** `on_source_antennas`  
**value:** List of on source antennas

11. **Source name:** [already exists]
**key:** `src_name`  
**value:** Current primary source

12. **Primary RA:** [already exists]
**key:** `ra`  
**value:** Current primary RA

13. **Primary Dec:** [already exists]
**key:** `dec`  
**value:** Current primary dec

14. **Primary Dec:** [already exists]
**key:** `dec`  
**value:** Current primary dec





