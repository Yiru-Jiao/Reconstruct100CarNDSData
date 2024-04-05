# Trajectory reconstruction of crashes and near-crashes from 100-Car NDS time-series data
This repository reconstructs bird's eye view trajectories of vehicles involved in crashes and near-crashes from 100-Car Naturalistic Driving Study (NDS) radar data.

## 100Car Naturalistic Driving Study (NDS)
>The 100-Car NDS was an instrumented-vehicle study conducted in the Northern Virginia / Washington, D.C. area over a 2 year period in early 2000s [^1]. The primary purpose of the study was to collect large scale naturalistic driving data. To this end, the instrumentation was designed to be unobtrusive, study participants were given no special instructions, and experimenters were not present. Approximately 100 vehicles were instrumented with a suite of sensors including forward and rearward radar, lateral and longitudinal accelerometers, gyro, GPS, access to the vehicle CAN, and five channels of compressed digital video. 
[^1]: Dingus, T.A., Klauer, S.G., Neale, V.L., Petersen, A., Lee, S.E., Sudweeks, J., Perez, M.A., Hankey, J., Ramsey, D., Gupta, S. and Bucher, C., 2006. The 100-car naturalistic driving study, Phase II-Results of the 100-car field experiment DOT-HS-810-593. United States. Department of Transportation. National Highway Traffic Safety Administration.

From the data collection, an event database has been compiled for 68 crashes and 760 near crashes, as defined in the table below [^2]. Note that 75% of the single vehicle crashes were low-g force physical contact or tire strikes; in other words, most of the crashes involved very minor physical contact. 
[^2]: Neale, V.L., Dingus, T.A., Klauer, S.G., Sudweeks, J. and Goodman, M., 2005. An overview of the 100-car naturalistic study and findings. National Highway Traffic Safety Administration, 05-0400.

|Event Category | Definition|
|---|---|
| Crash | Any contact between the subject vehicle and another vehicle, fixed object, pedestrian pedacyclist, or animal. |
| Near Crash | Defined as a conflict situation requiring a rapid, severe evasive maneuver to avoid a crash. |
| Incidents | Conflict requiring an evasive maneuver, but of lesser magnitude than a near crash. |

Including time-series sensor data, event context narratives, and manually remarked descriptions of these events, this database is now made public [^3] under a license of CC0 1.0. The time-series profile for each event contains radar and accelerometer data spanning 30s before the event and 10s after the event. This allows for trajectory reconstruction for the vehicles involved in the events.
[^3]: Custer, K., 2018. 100-Car data. VITTI. https://doi.org/10.15787/VTT1/CEU6RB

## Reconstructed examples of crashes
Not all of the events can be reconstructed due to the missing values, inaccuracy of sensing, and the lack of a ground truth. Subsequently, matching the target vehicle among the detected vehicles in each event is neither trivial. In this repository, 9 crashes and 128 near-crashes are matched based on the restriction that there is not sufficient space for a undetected vehicle. The following example visualises one of the reconstructed and matched crashes. For the rest of the examples, please refer to the folder ./visual_examples.
![til](./visual_examples/event_8360.gif)

## To repeat/adjust the processing
### Python libarary requirements
`pandas`, `tqdm`, `numpy`, `matplotlib`

### Wrokflow
**Step 1.** Download the raw data from [^3] in the folder `RawData`. This include: `100CarVehicleInformation_v1_0.txt`, `100CarEventVideoReducedData_v1_5.txt`, `HundredCar_Crash_Public_Compiled.txt`, `HundredCar_NearCrash_Public_Compiled.txt`, `Researcher Dictionary for Vehicle Data v1_0.pdf`, `Researcher Dictionary for Video Reduction Data v1.3.pdf`, and `DataDictionary_TimeSeries_v1_2.pdf`

**Step 2.** Convert `100CarVehicleInformation_v1_0.txt` into `100CarVehicleInformation.csv` using microsoft excel or other data sheet tools, and rename the column names based on corresponding data dictionary; similarly, convert the `100CarVehicleInformation_v1_0.txt` into `100CarEventVideoReducedData.csv`, rename and remain the columns of `webfileid`, `vehicle webid`, `event start`, `event end`, `event severity`, `target type`, `event nature`, then remove "Conflict with " in the descriptions and rename the column name `event nature` by `target`

**Step 3.** Run `preprocessing_100Car.py`

**Step 4.** Run `processing_100Car.py`

**Step 5.** Run `event_matching.py`, which can be adjusted for your own matching

**Step 6.** Use `visualiser.ipynb` to observe the reconstructed events

## Copyright
Copyright (c) 2024 Yiru Jiao. All rights reserved.

This work is licensed under the terms of the MIT license. For a copy, see <https://opensource.org/licenses/MIT>.
