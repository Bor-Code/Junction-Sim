# Signal Control Policies

`junction-sim` implements six distinct signal control paradigms conforming to the runtime `SignalController` protocol:

1. **Fixed-Time Controller** (Cyclic predetermined allocation based on Webster's formula)
2. **Actuated Controller** (Vehicle detector and gap-out adaptation)
3. **Max-Pressure Controller** (Network queue pressure optimization)
4. **Coordinated Controller** (Arterial corridor green-wave progression)
5. **Reservation Controller** (Autonomous Connected Vehicle space-time reservation grid)
6. **Reinforcement Learning Controllers** (Tabular Q-Learning and Deep Q-Network)

---

## 1. Controller Protocol

All controllers implement the `SignalController` protocol defined in `junction_sim.controllers.protocol`:

```python
class SignalController(Protocol):
    def decide(self, context: ControllerContext) -> ControllerDecision: ...
```

At each simulation step, the engine supplies a `ControllerContext` containing:
- `current_time`: Current simulation epoch in seconds.
- `active_phase_id`: Current active signal phase.
- `signal_state`: Active signal state (`GREEN`, `YELLOW`, or `ALL_RED`).
- `is_in_transition`: Boolean flag indicating whether the phase is currently clearing.
- `queue_lengths`: Dictionary mapping each lane ID to its current vehicle count.

The controller responds with a `ControllerDecision`:
- `target_phase_id`: Desired next phase ID (or `None` to maintain cyclic progression or keep active phase).
- `reason`: Diagnostic tag describing why the decision was taken.

---

## 2. Fixed-Time Controller (`FixedTimeController`)

### Concept

The Fixed-Time controller executes a predetermined, cyclic signal schedule where each phase receives a static green time followed by yellow and all-red clearing intervals.

### Timing Formula (Webster 1958)

For an isolated intersection with $N$ phases, the optimal cycle length $C_0$ minimizing total vehicular delay is given by:

$$C_0 = \frac{1.5 L + 5}{1 - Y}$$

Where:
- $L$ is the total lost time per cycle (sum of yellow and all-red clearing intervals across phases).
- $Y = \sum_{i=1}^N y_i$ is the total flow ratio, where $y_i = \max_m (q_m / s_m)$ is the critical flow ratio for phase $i$, $q_m$ is the arrival flow rate, and $s_m$ is the saturation flow rate.

The effective green time for each phase is allocated proportionally to its critical flow ratio:

$$g_i = (C_0 - L) \cdot \frac{y_i}{Y}$$

---

## 3. Actuated Controller (`ActuatedController`)

### Concept

The Actuated controller dynamically adjusts green times based on real-time vehicle arrivals detected on lane approach queues.

### Mechanics

- **Minimum Green (`min_green`)**: Guarantees a minimum green window to safely discharge standing queues before any phase change can occur.
- **Maximum Green (`max_green`)**: Upper limit preventing phase starvation on competing approaches under persistent heavy demand.
- **Vehicle Extension & Gap-Out (`headway_threshold`)**:
  - If vehicles continue arriving with headways smaller than the extension threshold, the phase is extended by small intervals.
  - If no vehicle is detected or the standing queue reaches zero (`gap_out`), the controller initiates phase termination early.

---

## 4. Max-Pressure Controller (`MaxPressureController`)

### Concept

Max-Pressure control is an acyclic, state-dependent distributed policy derived from queuing network theory (Varaiya 2013). It guarantees maximum stable throughput under arbitrary admissible arrival rates without requiring prior knowledge of arrival statistics.

### Pressure Formulation

For each movement $m = (l_{in}, l_{out})$, the pressure $P_m$ is defined as the upstream queue length:

$$P_m = Q_{in}(l_{in})$$

For each phase $p \in \mathcal{P}$, the total phase pressure is the sum of saturation-weighted pressures of all movements permitted by that phase:

$$W(p) = \sum_{m \in \mathcal{M}(p)} s_m \cdot P_m$$

---

## 5. Coordinated Controller (`CoordinatedController`)

### Concept

The Coordinated controller optimizes traffic progression along multi-intersection arterial corridors (Green Wave). By synchronizing cycle lengths and establishing directional phase offsets, vehicle platoons pass through successive intersections without stopping.

### Offset Formulation

For intersection $i$ along an arterial corridor at distance $d_i$ from the master reference junction, with progression speed $v_{\text{prog}}$ and common cycle length $C$:

$$\theta_i = \left(\frac{d_i}{v_{\text{prog}}}\right) \pmod C$$

---

## 6. Reservation Controller (`ReservationController`)

### Concept

Designed for Connected and Autonomous Vehicles (CAVs), the Reservation controller implements Autonomous Intersection Management (AIM) over a discrete space-time conflict grid.

### Mechanics

- The central junction is discretized into a 2D spatial grid (e.g. 10x10 cells).
- Approaching CAVs request a conflict-free space-time trajectory trajectory $\mathcal{T} = \{(x, y, t)\}$ through the junction.
- If all cells along the trajectory are unreserved during the required arrival window, the reservation is confirmed and the vehicle proceeds without stopping.
- Eliminates fixed phase switching delays and lost clearance times.

---

## 7. Reinforcement Learning Controllers (`QLearningController` & `DQNController`)

### Concept

Learns optimal signal switching policies through trial-and-error interactions in a Gymnasium-style environment (`JunctionEnv`).

- **Tabular Q-Learning**: Quantizes continuous queue lengths and elapsed phase times into discrete states, updating action-values $Q(s, a)$ via temporal difference learning.
- **Deep Q-Network (DQN)**: Multi-layer perceptron neural network approximating action-values directly from vector observations, stabilized by experience replay buffers and target networks.
- **Reward Functions**: Supports `queue_penalty`, `delay_penalty`, and `throughput` objective formulations.

---

## 8. Comparative Evaluation Summary

| Controller | Paradigm | Complexity | Best Suited For | CAV Support |
| :--- | :--- | :--- | :--- | :---: |
| **Fixed-Time** | Cyclic static | $O(1)$ | Predictable, steady traffic | No |
| **Actuated** | Dynamic gap-out | $O(\text{lanes})$ | Variable isolated arrivals | No |
| **Max-Pressure** | Queue differential | $O(\text{phases} \times \text{movements})$ | Network grids and surge traffic | No |
| **Coordinated** | Progression offset | $O(1)$ | Arterial corridors and green waves | No |
| **Reservation** | Space-time AIM | $O(\text{cells} \times \Delta t)$ | 100% CAV autonomous fleets | Yes |
| **DQN / RL** | Neural policy | $O(\text{FLOPs})$ | Non-linear, complex demand patterns | Mixed |
