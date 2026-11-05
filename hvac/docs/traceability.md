# Requirements and demo evidence
| Requirement | How to verify |
|---|---|
| FR-01 | Import a CSV with humidity 101. The file and row are identified; the previous session remains intact. |
| FR-02–03 | Play, pause, step and reset. Confirm current reading, units, occupancy, mode, reason and chart. |
| FR-04–06 | Run thermostat boundary, hold, vacancy, manual precedence and gap tests in tests/test_roomwise.py. |
| FR-07–08 | Change settings, try inverted bounds; inspect before/after history, restart and reopen the session. |
| FR-09–11 | Run default dataset to end and compare with README reference totals. Test excluded intervals and zero baseline. |
| NIST CPS design reference | Functional: exclusive modes. Human: labeled manual control. Timing: dataset time. Data: validated readings. Trustworthiness: reproducible tests and event logs. Boundaries: all actuators are simulated. |
Reference: https://doi.org/10.6028/NIST.SP.1500-201. These design links do not assert certification.
