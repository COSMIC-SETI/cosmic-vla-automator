# Commensal observing with VLASS

Here I aim to begin planning what the automator will do during VLASS-style 
observing.

During VLASS observations:
- The telescope observes a continuous track varying in RA across the sky 
- These tracks overlap
- A source is typically present for at most 5 seconds as the primary field of 
view passes over it

## Phase 1

For expedient development, we could follow an easier, discrete 
approach to begin with.  

### 1.

In this first figure, the telescope is scanning in RA as shown. At time 
t<sub>1</sub>, the primary field of view of the telescope is centered on 
RA<sub>1</sub>, and at t<sub>2</sub>, RA<sub>2</sub>. RA<sub>1</sub> and 
RA<sub>2</sub> are two primary beamwidths apart. 

![Fig. 1](diagrams/vlass_1b.svg)

### 2.

The automator instructs the processing nodes to record from t<sub>1</sub> to 
t<sub>2</sub>. It also instructs the phase center to be at C as
follows:

![Fig. 2](diagrams/vlass_2b.svg)

### 3. 

We know that VLASS scans overlap in DEC, so we can constrain target sources to 
lie in a strip narrower than the primary field of view of the telescope. The 
targets to be observed are given in red. By limiting them within the 
primary field of view centered on C, we ensure that each source is 
recorded for a full transit of the primary field of view. 

![Fig. 3](diagrams/vlass_3b.svg)

### 4. 

Not all the stars within the circle around C will be visible for 
the full width of the primary field of view. The horizontal red lines give an 
indication of the portion of RA within which they are recorded as the primary 
field of view passes.

![Fig. 4](diagrams/vlass_4b.svg)

The automator will (via the target selector) issue coordinates for sources (in 
red in the diagram) to the recipe file generator. The recipe file should 
contain the start and stop coordinates for each source. The beamformer will be 
instructed to beamform on each of the sources, either zeroing the coefficients 
when a source leaves the field of view or ignoring the data during this time. 

### 5.

In this 'easy mode', the automator deals with discrete recordings, each covering a 
transit equivalent to two beamwidths. Each of these discrete recordings is 
handled completely separately with a separate beamformer recipe file. After 
recording, processing (upchannelisation, beamforming, SETI search and cleanup)
takes place. Some sections of sky are inherently missed, depending on how long 
processing takes. 

![Fig. 4](diagrams/vlass_5b.svg)

**Pros:**

- No need to manage phase centers calculated from overlapping segments of data
- Improvement in sky coverage can be made by speeding up processing and 
bringing segments closer together

**Cons:**

- Even with the best case processing time, portions of sky will still be missed
since phase centers must be calculated from separate segments of recorded data. 

## Phase 2

Here, we are able to shrink processing enough such that we can have the field
of view around each phase center overlap. 

In this case, since the FPGAs must pick a phase center for any given time sample,
processing the overlapping data blocks requires re-phasing them to the appropriate
pointing when the data are reused.

This way, none of the sky is missed. 
This means that overlapping sections of the recorded data are needed for each 
phase center calculation. We can also confine targets to a simple rectangular 
region around each phase center.

![Fig. 4](diagrams/vlass_6b.svg)

The overlapping sections of the recorded data are shown below:

![Fig. 4](diagrams/vlass_7b.svg)

For an approach like this, the automator would precalculate target lists, the 
locations of phase centers, and beamformer recipe files in advance at the start 
of a VLASS scan. Then, recording and processing would take place autonomously 
and without intervention from the automator until the scan is completed. 

