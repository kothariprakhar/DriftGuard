# Shadow Holdout

The public pilot repository intentionally does **not** include shadow-holdout scenarios.

For the future public benchmark release, the shadow holdout should:

- remain outside routine tuning
- be run only once for a selected configuration
- be used to detect benchmark-shaped improvements

The split policy is now explicit in [`benchmark/scenarios/splits.json`](/Users/prakharkothari/Documents/DriftGuard/benchmark/scenarios/splits.json), where `shadow_holdout` is marked private, frozen, and hidden.

The local runner now also includes hidden-run registry scaffolding:

- hidden manifests require explicit opt-in with `--allow-hidden`
- repeated hidden runs are blocked by default
- local records can be inspected with `python3 -m driftguard list-hidden-runs`
