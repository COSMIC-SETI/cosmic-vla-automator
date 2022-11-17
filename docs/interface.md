# Interfacing requirements for the automator

The Automator's actions fall into 2 categories:
	- Command: issuance of an event on the telescope
	- Reflect: reflection on the state of an aspect of the telescope


## Commands:

### 1. Observation possible?
This commands the telescope to report an observation that is possible to undertake.

Interface-method call: `command_observation_possible()`

It sets the `COMMAND` key of the `observations_possible` redis-hash to a value of `"QUERY"`.

### 2. Observe.
This commands the telescope to undertake an observation that it reported as possible.

Interface-method call: `command_observation(observation)`
- `observation`: the value returned by the (`reflect_observation_possible()` Interface-method)[#Reflections:_1._Observation_possible.].

It sets the `COMMAND` key of the `observation` redis-hash to a value of `observation`.

## Reflections:

### 1. Observation possible.
This reflects on the response of the (`command_observation_possible()` Interface-method)[#Commands:_1._Observation_possible?].

It returns the value of the `STATUS` key in the `observations_possible` redis-hash, only replacing the value with the Pythonic `None` if the value is `"None"`.

### 2. Observation
This reflects on the status of an observation that is the result of the (`command_observation()` Interface-method)[#Commands:_1._Observe.].

It returns the value of the `STATUS` key in the `observation` redis-hash. The value's range is: [`"Pending"`, `"Succeeded"`, `"Failed"`]. A value outside of this range causes a `ValueError` to be raised.


