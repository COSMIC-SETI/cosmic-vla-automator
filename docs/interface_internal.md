
The responses of the Automator's actions are separated from the issuance of the action, in order open actions up to being carried out over any abstract channel, as opposed to just the process's call stack. The interface
methods thusly fall into 2 categories:
	- Command: issuance of an event on the telescope
	- Reflect: reflection on the state of an aspect of the telescope

Because this dichotomy essentially makes the actions asynchronous, the reflection is triggered by a change in the associated redis-hash (enabled by keyspace monitoring). Reflection methods return a value, which must be a primitive or a collection of primitives.

## Actions:

### 1. Observation possible?

The action is to query the telescope about whether or not an observation is possible, and if so what that observation is.

Command method call | Description
-|-
`command_observation_possible()` | Set the `COMMAND` key in the `observations_possible` redis-hash to `"QUERY"`.


Reflection method call | Description
-|-
`reflect_observation_possible()` | Return the value of the `STATUS` key in the `observations_possible` redis-hash. **Only a value of `"None"` is altered, to the Pythonic `None`**.

### 2. Observe.
This action commands the telescope to undertake an observation that it reported as possible.

Command method call | Description
-|-
`command_observation(observation)` | Set the `COMMAND` key of the `observation` redis-hash to `observation`, the value returned by the `reflect_observation_possible()` method.

Reflection method call | Description
-|-
`reflect_observation()` | Return the value of the `STATUS` key in the `observation` redis-hash. The value's range is: [`"Pending"`, `"Succeeded"`, `"Failed"`]. A value outside of this range causes a `ValueError` to be raised.