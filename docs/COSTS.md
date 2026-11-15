# Costs and resources

**Policy.** The procedural v0.1.0 needs no paid infrastructure. No agent may rent GPUs, buy
credits, call metered APIs, subscribe to services or download model weights without the
owner's explicit approval for that specific spend. Approved runs are capped, and the actual
figures are recorded in the handoff. Authorised budget today: **€0**.

Figures marked *est.* are estimates to be replaced by measurements (the integrator fills the
"measured" column in WP12 §7.2). Prices were read on 2026-11-15 and are volatile.

## Local resources

Bootstrap machine: Apple M5, 10 cores, 24 GB RAM, 67 GB free disk (93 % full — the binding
constraint). Ubuntu Server is the second supported platform.

| Item | Estimate | Measured |
|---|---|---|
| Raw downloads (Catastro 4 MB, IGN MDT+MDS 175 MB, OSM < 20 MB) | ≈ 200 MB | |
| Intermediates + scene | < 300 MB | |
| Render layers (≈ 11 300 × 6 500 px, 3–4 PNG layers) | < 300 MB | |
| Tile set (≈ 400 tiles) | 25–60 MB | |
| Python env + two `node_modules` + Playwright Chromium | ≈ 1.5 GB | |
| GIS scene build | minutes, < 4 GB RAM | |
| Full render | budget ≤ 10 min, ≤ 8 GB RAM | |
| Tile export | < 2 min | |

Each task worktree repeats environments and build outputs: keep worktrees outside Dropbox
(`WORKTREE_ROOT`), and `make clean` finished ones.

## Size model

For AOI side `L` (m), scale `s` (px/m), heading 45°, pitch φ, relief `Δz` (m), tile size `T`:

```
width  ≈ √2 · L · s
height ≈ √2 · L · s · sin φ + Δz · s · cos φ
tiles  ≈ (4/3) · ceil(width / T) · ceil(height / T)
bytes  ≈ tiles · b̄              (b̄ = mean bytes per tile, measured in WP06)
```

Villena v0.1.0 (`L` = 1000, `s` = 8, φ = 30°, `Δz` ≈ 120 est., `T` = 512):
11 314 × ≈ 6 500 px → 23 × 13 = 299 base tiles → ≈ 400 tiles. At an assumed 60–150 kB per
tile: 24–60 MB, well inside the 250 MB budget. Doubling `s` quadruples everything.

## GitHub

| Limit | Value | Our position |
|---|---|---|
| Pages published site | 1 GB | internal budget 250 MB, checked by `make size-check` |
| Pages bandwidth | 100 GB / month (soft) | a full-zoom visit loads a few MB; not a concern at this scale |
| Pages deploy timeout | 10 min | build is seconds; tiles arrive as one archive |
| Single file in Git | 100 MiB hard block | nothing over 1 MB without a reason |
| Repository size | 1 GB recommended | tiles live in a release asset, not in Git |
| Release asset | < 2 GiB each | tile archive est. 25–60 MB |
| Actions minutes | free for public repositories | CI renders nothing and downloads no geodata |

## AI subscriptions

Quotas for the owner's Claude, Codex and Gemini plans are not known to the agents. Each
handoff records the model and effort actually used so consumption can be tracked. Rules that
keep usage sensible: the cheapest model that fits (`docs/AGENT_ROUTING.md`); `max`/`xhigh`/
`ultra` only for demonstrated blockers; reviews through chat bundles when no client exists.

**DeepSeek has no subscription coding client.** Agentic use is metered API
(`deepseek-flash` ≈ $0.15–0.30 per million input tokens, read 2026-11-15). The free route is
the chat UI with a context bundle. API use needs approval like any other spend.

## Optional image-generation experiment (WP10) — not authorised

Proposed ceiling if the owner chooses to run it: **€150**, in stages, each needing its own go:

| Stage | Content | Estimate |
|---|---|---|
| A | Harness, metrics, no-model controls, design | €0 |
| B | 25 regions × ≤ 4 attempts, two models, API (fal.ai ≈ $0.03/MP Qwen 2511, $0.01/MP FLUX.2 klein 4B) or rented GPU (48 GB ≈ $0.33–0.69/h) | €5–50 |
| C | Small LoRA (≈ 40 pairs), only after a "go" from B | €15–70 |

Cost model — fill with **measured** values from stage B, never with another project's:

```
N         = regions needed = ceil(width / S) · ceil(height / S)        S = region stride in px
attempts  = N / a                                                      a = acceptance rate (0–1]
compute   = attempts · t · p_gpu / 3600      (rented GPU: t = s per attempt, p_gpu = €/h)
        or  attempts · m · p_mp              (API: m = megapixels per attempt, p_mp = €/MP)
review    = attempts · r                                               r = human seconds per attempt
total     = compute · (1 + R) + setup                                  R = expected re-render fraction
storage   = N · b̄_ai                                                   added to the site budget
```

For scale only: Villena at 512-px stride needs about 23 × 13 ≈ 300 regions. Isometric NYC's
published figures cannot be transferred: it is a different area, tile size, pixel density,
model and data path, and its author reports heavy manual QA.

Human review time is a real cost: at 300 regions, 4 attempts and 20 s per look, that is
almost 7 hours of the owner's attention before any re-render.
