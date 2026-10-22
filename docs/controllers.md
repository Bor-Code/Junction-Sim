# Signal Control Policies

`junction-sim` implements three distinct signal control paradigms conforming to the runtime `SignalController` protocol:

1. **Fixed-Time Controller** (Cyclic predetermined allocation)
2. **Actuated Controller** (Vehicle detector and gap-out adaptation)
3. **Max-Pressure Controller** (Network queue pressure optimization)

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

### Operation in Simulation

- Phase durations are strictly bounded by `green_duration`.
- Transition to the next phase occurs strictly when the elapsed green time reaches `green_duration`.
- Does not respond to transient fluctuations in queue lengths.

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

### Decision Logic

```text
if elapsed_green < min_green:
    hold green (reason: "min_green")
elif active_phase_queue > 0 and elapsed_green < max_green:
    extend green (reason: "vehicle_extension")
else:
    terminate phase (reason: "gap_out" or "max_green_exceeded")
```

---

## 4. Max-Pressure Controller (`MaxPressureController`)

### Concept

Max-Pressure control is an acyclic, state-dependent distributed policy derived from queuing network theory (Varaiya 2013). It guarantees maximum stable throughput under arbitrary admissible arrival rates without requiring prior knowledge of arrival statistics.

### Pressure Formulation

For each movement $m = (l_{in}, l_{out})$, the pressure $P_m$ is defined as the difference between the upstream queue and the downstream queue:

$$P_m = Q_{in}(l_{in}) - Q_{out}(l_{out})$$

In an isolated intersection where outgoing links have infinite sink capacity, the pressure simplifies to the upstream queue length:

$$P_m = Q_{in}(l_{in})$$

For each phase $p \in \mathcal{P}$, the total phase pressure is the sum of saturation-weighted pressures of all movements permitted by that phase:

$$W(p) = \sum_{m \in \mathcal{M}(p)} s_m \cdot P_m$$

### Switching Rules

1. **Minimum Green Enforcement**: The active phase is held until `min_green` has elapsed.
2. **Maximum Pressure Selection**:
   - The controller calculates $W(p)$ for all candidate phases.
   - If the candidate phase with maximum pressure $p^* = \arg\max_p W(p)$ differs from the active phase and the pressure advantage exceeds a switching threshold:
     $$W(p^*) - W(p_{curr}) > \Delta_{threshold}$$
     the controller signals a transition to $p^*$.
3. **Starvation Prevention**: Enforces `max_green` to prevent indefinite hold under extreme unidirectional overload.

---

## 5. Comparative Evaluation Summary

| Feature | Fixed-Time | Actuated | Max-Pressure |
| :--- | :--- | :--- | :--- |
| **Adaptability** | Low (Static) | Moderate (Local Headway) | High (Queue Differentials) |
| **Computational Complexity** | $O(1)$ | $O(\text{lanes})$ | $O(\text{phases} \times \text{movements})$ |
| **Best Suited For** | Predictable, steady traffic | Low to moderate variable traffic | Complex, highly asymmetric or surge traffic |
| **Wasted Green** | High during low demand | Very Low | Low |
