# Physics Scope

Earth Replica uses "all physical laws apply" as a long-term direction, not as an immediate claim of perfect planetary simulation.

The practical approach is progressive fidelity:

1. Start with local, bounded simulations.
2. Make physical assumptions explicit.
3. Validate simulated output against observations.
4. Add specialized solvers when a domain needs more fidelity than Genesis can provide.
5. Couple domains only when the coupling can be tested.

## Initial Genesis-Backed Domains

### Rigid Bodies

Use Genesis for objects, terrain interactions, vehicles, robots, structures, agents, and contact-rich local scenes.

### Fluids

Use Genesis fluid solvers for local water, gas, and flow prototypes. For engineering-grade fluid dynamics, bridge to dedicated tools such as OpenFOAM or other CFD solvers.

### Deformables and Materials

Use Genesis FEM, MPM, PBD, and related solvers for deformable objects, granular materials, cloth-like surfaces, soil-like interactions, and soft-body experiments.

### Rendered Observations

Use rendering to produce visual and sensor-like observations from simulated state. Rendered output should be labeled as simulated unless it is directly tied to real imagery.

## Future Specialized Domains

Some physical domains should not be forced into a general-purpose simulator too early:

- Weather and climate
- Ocean circulation
- Seismology
- Electromagnetism
- Acoustics
- Chemistry
- Biology
- Quantum-scale effects
- General relativity

These domains need specialized models, data, validation standards, and in many cases high-performance computing.

## Fidelity Levels

Earth Replica should label physical modules using these fidelity levels:

- `illustrative`: useful for visualization, not prediction.
- `interactive`: plausible behavior for local interaction.
- `engineering`: validated for a defined class of measurements.
- `research`: scientifically grounded and benchmarked, but still assumption-bound.
- `observed`: directly measured or assimilated from sensor data.

No module should claim universal accuracy.
