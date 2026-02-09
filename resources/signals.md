| Signal Name         | Unit              | Meaning                     |
|----------------------|-------------------|------------------------------|
| presence_s           | seconds           | Duration a person has been in the frame. |
| doorbell_rings       | count             | Number of times the doorbell button has been pressed (decays over time). |
| net_disp             | units             | Net displacement of the person's centroid (how far they moved from start). |
| motion_E             | units             | Local motion energy (how much pixel change around the person). |
| velocity             | units / s         | Speed of the person's centroid. |
| head_yaw_rate        | units / s         | Rate of change of head yaw (looking around quickly). |
| head_osc             | count / window    | Head oscillation count (shaking head). |
| head_down            | [0,1]             | Fraction of time head is pitched down (looking at phone/feet). |
| dir_flip             | count / window    | Number of times the person changed direction (pacing). |
| osc_energy           | units             | Energy of the oscillation (how erratic the movement is). |
| stop_go              | count / window    | Number of times the person stopped and started moving. |
| hand_fidget          | units             | High-frequency movement of the hands (nervousness). |
| movinet_pressure     | [0,1]             | Pressure score derived from MoViNet violence detection probability. |
| loitering_score      | [0,1]             | Score indicating loitering behavior. |
| loitering_type       | string            | Type of loitering (STATIONARY, PACING, DISPLACED). |
| loitering_time       | seconds           | Duration the person has been loitering. |
| loitering_radius     | units             | Radius of the area the person is loitering in. |
| weapon_confirmed     | boolean           | 1.0/0.0 if a weapon is confirmed by detection + persistence. |
| weapon_cooldown      | seconds           | Time remaining before weapon confirmation expires. |
