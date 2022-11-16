# Interfacing requirements for the automator

## Status keys:

These keys should be set as close to the originating source as possible. E.g. 
in the case of the VLA, `mcast2redis.py` should set some of these directly 
upon receiving a metadata packet.  

These keys are expected to be updated the instant they change. There is no 
need for timestamps as Redis provides this already. 

1. **Current fengine status:**  
**key:** `fengine_status`  
**value:** JSON dict containing `{<antenna>:<status>}`  
**status:** can be `enabled`, `disabled`, `error`

2. **Current observing mode:**  
**key:** `obs_mode`  
**value:** string containting observing mode  
**status:** [What possibilities currently exist?] 

3. **Recording output directories:**  
**key:** `<host/instance>:raw_dir`  
**value:** File path to current directory in which raw files will be written

4. **Current processing status**  
**key:** `<host/instance>:proc_stat`  
**value:** Current status of processing  
**status:** `processing`, `idle`, `error`

5. **Current processing type/description**  
**key:** `<host/instance>:proc_name`  
**value:** Name of current processing state  

6. **Processing output directory**  
**key:** `<host/instance>:proc_dir`  
**value:** Directory in which processing data products are currently being 
written    


## Actions

For these commands, implement an API or library that can be imported, from 
which the required commands can be imported. 

For example:
```
from telescope_control import record
```

### record_conditional

Note: must be non-blocking 

Attempts to record based on conditions stored in config file.  

**args:**  
- `config` (str): file path to config file (Not strictly necessary for COSMIC, but I'm
asking for this here to help us keep it in the same place).
- `raw_dir` (str): file path to output directory (over-arching, this function could create 
new subdirectories beneath this, for example).
- `instances` (List[str]): List of instances for which recording should proceed on if 
conditions are met. 

**returns:**
- True if conditions are met and recording is actually going to take place
- False if conditions are not met and recording is not going to take place

### record

Note: must be non-blocking

**args:** 
- `duration` (float): recording duration in seconds  
- `raw_dir` (str): entire file path to final output directory 
- `instances` (List[str]): list of instances which must record

**returns:**
- True if succesfully requested
- False if not. 

### process

Note: must be non-blocking  

**args:** 
- `raw_dir` (str): file path to output directory 
- `instances` (List[str]): list of instances which must attempt processing

**returns:**
- True if succesfully requested
- False if not. 

### stop_recording

Note: can be blocking. 

**args:** 
- `instances` (List[str]): list of instances which must immediately stop 
recording

**returns:**
- True if succesful
- False if not

### configure

Note: must be non-blocking  

**args:**  
- `mode` (str): observing mode

**returns:**
- True if succesfully requested  
- False if not. 

### delete

- Note: expected to be blocking.

**args:**  
- `instances` (List[str]): list of instances which must perform local deletion  
- `directory` (str): The full file path to a directory whose entire contents 
must be deleted

**returns:**
- List[str] of instances for which deletion was successful.  

