# 05 — Image-generation models for optional tile restyling

**Verification date: 2026-11-15.** Everything below was checked on that date against Hugging Face (Hub API and model cards), the Diffusers `main` branch, and vendor pricing pages. No weights were downloaded and nothing was run: **all VRAM, speed and quality figures are from third-party sources, not measured by us.**

Evidence labels used throughout:

- **[V]** verified on a primary source (HF Hub API, model card, licence file, Diffusers source, vendor price page).
- **[3P]** third-party source only (blog, aggregator, community card). Treat as a planning estimate.
- **[U]** not verified in this session (from prior knowledge or inference). Listed again in section 8.

Scope reminder: restyling is an OPTIONAL step after the procedural render. No money is spent without owner approval; the proposed experiment cap is €150.

---

## 0. Summary

| | |
|---|---|
| Primary model | `Qwen/Qwen-Image-Edit-2511` — Apache-2.0 — `QwenImageEditPlusPipeline` |
| Fallback model | `black-forest-labs/FLUX.2-klein-4B` (and `-base-4B` for LoRA/inpaint) — Apache-2.0 — `Flux2KleinPipeline` / `Flux2KleinInpaintPipeline` |
| Technique | Neighbour-conditioned infill on a single composite input (Isometric NYC style), known pixels pasted back, then palette quantisation |
| Hardware | One rented 48 GB GPU (A6000/A40/L40S), or 80 GB A100 to avoid offloading |
| Benchmark cost | About $5–25 for 100 generations; about $40–60 including an optional LoRA stage. Well under the €150 cap |
| Biggest risk | No source shows any of these models giving seamless, geometry-faithful tiles zero-shot. Isometric NYC needed a fine-tune, manual QA and manual fixes |

The newest and highest-ranked open-weights editors (Qwen-Image-2.1, FLUX 3 Image Klein, MiniMax H3-Image) are **not** recommended because their licences are non-commercial/research or unverified (section 2).

---

## 1. Qwen Image Edit family

### 1.1 Model IDs and licences

From the Hub API listing for author `Qwen` ([source](https://huggingface.co/api/models?author=Qwen&search=Image&sort=lastModified&direction=-1&limit=50)) **[V]**:

| Model ID | Created | Task tag | Licence | Notes |
|---|---|---|---|---|
| `Qwen/Qwen-Image-Edit` | 2025-08-17 | image-to-image | apache-2.0 | Single input image |
| `Qwen/Qwen-Image-Edit-2509` | 2025-09-22 | image-to-image | apache-2.0 | "Edit Plus", multi-image |
| `Qwen/Qwen-Image-Edit-2511` | 2025-12-17 | image-to-image | apache-2.0 | Latest Apache-licensed edit model |
| `Qwen/Qwen-Image-Layered` | 2025-12-17 | image-text-to-image | apache-2.0 | Layer decomposition, not restyling |
| `Qwen/Qwen-Image` / `Qwen/Qwen-Image-2512` | 2025-08 / 2025-12 | text-to-image | apache-2.0 | Base T2I; ControlNets target these |
| `Qwen/Qwen-Image-2.1` | 2026-09-14 | text-to-image (also edits) | **other: Qwen Research License** | Unified generate+edit, 7B |
| `Qwen/Qwen-Image-2.1-Turbo` | 2026-10-09 | text-to-image | other | Not inspected further |
| `Qwen/Qwen-Image-2.1-PE-I2I` / `-PE-T2I` | 2026-09-20 | — | other: Qwen Research License | Prompt rewriters (fine-tuned VLM), not image models ([card](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I)) |

There is **no `Qwen-Image-Edit` release dated 2026**; the edit line continues inside Qwen-Image-2.1.

- `Qwen-Image-Edit-2511` card: "Qwen-Image is licensed under Apache 2.0"; lists "mitigate image drift, improved character consistency" and integrated LoRA capabilities ([card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)) **[V]**.
- `Qwen-Image-2.1`: accepts "up to 10 reference images", supports local edits via "circles, painted annotations, or separate masks", examples at 2048×2048, 40 steps ([card](https://huggingface.co/Qwen/Qwen-Image-2.1)) **[V]**. Its licence grants use "FOR NON-COMMERCIAL PURPOSES ONLY", defined as "for research or evaluation purposes only"; output ownership is not addressed; Hangzhou jurisdiction ([LICENSE](https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE)) **[V]**. Publishing a public map made with it is not clearly "research or evaluation", so it is excluded.

### 1.2 Diffusers pipeline classes

Files in `src/diffusers/pipelines/qwenimage` on `main` ([source](https://github.com/huggingface/diffusers/tree/main/src/diffusers/pipelines/qwenimage)) and the docs page ([qwenimage.md](https://github.com/huggingface/diffusers/blob/main/docs/source/en/api/pipelines/qwenimage.md)) **[V]**:

| Class | Purpose |
|---|---|
| `QwenImagePipeline`, `QwenImageImg2ImgPipeline`, `QwenImageInpaintPipeline` | Base T2I / img2img / inpaint (`Qwen/Qwen-Image`) |
| `QwenImageEditPipeline` | `Qwen/Qwen-Image-Edit`, one image |
| `QwenImageEditInpaintPipeline` | Masked edit; docstring example uses `Qwen/Qwen-Image-Edit` |
| `QwenImageEditPlusPipeline` | `Qwen-Image-Edit-2509` and `-2511`, list of images |
| `QwenImageControlNetPipeline` (+ `pipeline_qwenimage_controlnet_inpaint.py`) | ControlNet on base `Qwen/Qwen-Image` |
| `QwenImageLayeredPipeline` | Layered |
| `QwenImage21Pipeline` (separate dir `qwenimage21`) | Qwen-Image-2.1; card says install Diffusers from GitHub `main` |

The Diffusers docs checkpoint table only lists up to `-2509`; the `-2511` card itself uses `QwenImageEditPlusPipeline` **[V]**.

### 1.3 Multi-image input

Read from `pipeline_qwenimage_edit_plus.py` ([source](https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_plus.py)) **[V]**:

- `image` takes a list. No hard cap in code; `batch_size` must be 1.
- Each image is resized twice, keeping aspect ratio: to about 384×384 area for the vision-language text encoder, and to about 1024×1024 area for the VAE.
- The prompt is prefixed with `Picture 1: … Picture 2: …` tokens.
- All image latents are concatenated **along the sequence dimension** with the noisy target latents; only the target part is denoised.
- Output size defaults to about 1 MP using the **last** image's aspect ratio.
- **There is no mask argument.**

Consequence: references are soft conditioning through attention. Nothing in the mechanism pins a reference pixel to an output pixel, so multi-image input alone cannot guarantee seam alignment or geometry fidelity (see section 3).

Practical image count: the model cards show 2-image examples. The "1–3 images work best" guidance for 2509 is **[U]**.

### 1.4 Inpainting / masked edit

`QwenImageEditInpaintPipeline` takes `image`, `mask_image`, `strength` (default 0.6), `padding_mask_crop`; white is repainted, black preserved. The mask is enforced by latent blending every step: `latents = (1 - init_mask) * init_latents_proper + init_mask * latents` ([source](https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_inpaint.py)) **[V]**.

Limits: it takes one source image (a list is treated as a batch, not as references), and the mask lives at latent resolution, so boundaries are softer than a pixel mask. Whether it loads `-2509`/`-2511` weights correctly is **[U]**.

### 1.5 ControlNet / depth conditioning

Hub search ([source](https://huggingface.co/api/models?search=Qwen-Image+ControlNet&sort=downloads&direction=-1&limit=30)) **[V]**:

- For base `Qwen/Qwen-Image` (Apache-2.0): `InstantX/Qwen-Image-ControlNet-Union`, `InstantX/Qwen-Image-ControlNet-Inpainting`, `DiffSynth-Studio/Qwen-Image-Blockwise-ControlNet-Canny` / `-Depth`.
- For `Qwen-Image-2512` (Apache-2.0): `alibaba-pai/Qwen-Image-2512-Fun-Controlnet-Union`.
- For `Qwen-Image-2.1`: `alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union` (licence `other`).
- **No general ControlNet for the Edit-2509/2511 checkpoints was found.** With edit models the input image itself is the structural condition.

Diffusers loads the InstantX union model through `QwenImageControlNetModel` + `QwenImageControlNetPipeline` (docstring example) **[V]**. This gives a second route: base Qwen-Image T2I + depth/canny ControlNet from our own renderer's depth buffer + a pixel-art LoRA.

### 1.6 LoRA

- Loading: `pipe.load_lora_weights(...)` works on Qwen pipelines (Diffusers quicktour and Lightning examples) **[V]**.
- Distillation LoRA: `lightx2v/Qwen-Image-Edit-2511-Lightning`, Apache-2.0, **4-step only**, claims "≈10x faster than standard 40-step inference"; also an FP8 checkpoint with the LoRA fused ([card](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning)) **[V]**.
- Guidance: `guidance_scale` is ineffective; use `true_cfg_scale` plus a `negative_prompt` (Diffusers docs) **[V]**. With true CFG each step costs two forward passes.
- Training tools **[3P]**: Ostris AI Toolkit (guide lists 32 GB+ recommended for 2511; users report 25–28.5 GB for 2509), kohya `musubi-tuner` (lighter), DiffSynth-Studio (scripts listed for Edit and Edit-2509) ([RunComfy guide](https://www.runcomfy.com/trainer/ai-toolkit/qwen-image-edit-2511-lora-training), [DiffSynth docs](https://diffsynth-studio-doc.readthedocs.io/en/latest/Pipeline_Usage/Model_Training.html)). A first-party Diffusers training script for Qwen edit was not confirmed **[U]**.
- Precedent: Isometric NYC fine-tuned Qwen Image Edit on about 40 input/output pairs; "The fine-tuning took ~4 hours and cost ~12 bucks" on oxen.ai ([source](https://cannoneyed.com/projects/isometric-nyc)) **[V]**.

### 1.7 Resolution

Edit Plus targets about 1 MP total, dimensions rounded to multiples of 32 (pipeline source) **[V]**. The 2511 card states no limits. Behaviour above about 1 MP for 2511 is **[U]**. Qwen-Image-2.1 documents 2048×2048 and 1536×2752 **[V]**.

For pixel art this is fine: generate at 1024² and downscale by an integer factor.

### 1.8 VRAM, steps, speed

| Configuration | Figure | Evidence |
|---|---|---|
| Transformer file size, BF16 | 40.9 GB | [V] [unsloth GGUF repo](https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF/tree/main) |
| GGUF Q8_0 / Q6_K / Q5_K_M / Q4_K_M / Q3_K_M / Q2_K | 22.4 / 17.9 / 15.4 / 12.8 / 9.92 / 7.74 GB | [V] same repo (file sizes, not peak VRAM) |
| Text encoder | Separate VLM, roughly 16 GB in BF16 | [U] |
| Fully on GPU, BF16 | 40 GB+ class; "offload required under 40 GB" | [3P] [community 4-bit card](https://huggingface.co/libaya/Qwen-Image-Edit-2511-4bit) |
| 24 GB card | Needs offload or quantisation; DFloat11 reports 22.7 GB peak with offload but 570 s/image on A100 (original Edit) | [3P] [DFloat11 card](https://huggingface.co/DFloat11/Qwen-Image-Edit-DF11) |
| A100, 2509, DFloat11 lossless | 30.2 GB peak, 102 s/image | [3P] [DFloat11 2509 card](https://huggingface.co/DFloat11/Qwen-Image-Edit-2509-DF11) |
| RTX 4090, nunchaku INT4, 40 steps | about 23 GB, about 2 min 44 s | [3P] (search result summary) |
| Default steps | Pipeline default 50; 2511 card example 40 with `true_cfg_scale=4.0`; Lightning 4 | [V] |
| `torch.compile` | about 2.4× speedup on A100 80 GB (base model, Diffusers docs) | [V] as a doc statement |

No like-for-like benchmark of 2511 + Lightning + GGUF on a 24 GB card was found. **Plan for 30–170 s per 40-step image and roughly 10× less with Lightning, and measure it in the first hour of the benchmark.**

Diffusers GGUF loading for the Qwen transformer (`from_single_file` + `GGUFQuantizationConfig`) is **[U]**; bitsandbytes 4-bit via `PipelineQuantizationConfig` is documented for `Qwen/Qwen-Image` ([quicktour](https://github.com/huggingface/diffusers/blob/main/docs/source/en/quicktour.md)) **[V]**.

### 1.9 Apple Silicon

- Diffusers examples annotate `.to("cuda")  # or "mps", "xpu", "cpu"` **[V]** — a doc comment, not a performance claim.
- MLX: `mflux-community/qwen-image-edit-2511-mflux-q8` (37.5 GB; other quantisations 24.7–56.6 GB), run with `mflux-generate-qwen-edit`, Apache-2.0 ([card](https://huggingface.co/mflux-community/qwen-image-edit-2511-mflux-q8)) **[V]**. No RAM or speed figures given.
- Verdict: plausible on a 64 GB+ Mac for a handful of tiles, speed unknown **[U]**. Do not plan the benchmark around it. The FLUX.2 klein 4B fallback (about 13 GB) is the realistic local option, also **[U]** on MPS.

---

## 2. Alternatives with open weights

### 2.1 Black Forest Labs

Hub listing ([source](https://huggingface.co/api/models?author=black-forest-labs&sort=lastModified&direction=-1&limit=60)) **[V]**.

| Model ID | Licence | Diffusers | Key facts |
|---|---|---|---|
| `black-forest-labs/FLUX.2-klein-4B` | **Apache-2.0** | `Flux2KleinPipeline` | 4B, T2I + multi-reference editing, 4 steps, "~13GB VRAM", RTX 3090/4070+ ([card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)) |
| `black-forest-labs/FLUX.2-klein-base-4B` | **Apache-2.0** (Hub tag) | same family | Undistilled; the one to fine-tune. Card not read **[U]** |
| `black-forest-labs/FLUX.2-klein-9B` (+ `-base-9B`, `-9b-kv`) | FLUX Non-Commercial License | `Flux2KleinPipeline`, `Flux2KleinInpaintPipeline` | 9B, "~29GB VRAM", 4 steps; filters or manual review required ([card](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B)) |
| `black-forest-labs/FLUX.2-dev` | FLUX Non-Commercial License | `Flux2Pipeline` | 32B, 50 steps (28 suggested), multi-reference, 4-bit variant `diffusers/FLUX.2-dev-bnb-4bit` ([card](https://huggingface.co/black-forest-labs/FLUX.2-dev)) |
| `black-forest-labs/flux-3-image-klein` (+ `-base`) | **FLUX Kommunity License v1.0** | `ModularPipeline`, Diffusers `main` only; no `flux3` dir | 5.6B, up to 10 reference images, 16 steps, peak "31 GB in BF16, 26 GB in FP8"; separate 9B prompt upsampler ([card](https://huggingface.co/black-forest-labs/flux-3-image-klein)) |
| `black-forest-labs/FLUX.1-Kontext-dev` | FLUX.1 [dev] Non-Commercial License | `FluxKontextPipeline` | Single-image editor, `guidance_scale=2.5` ([card](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)) |
| `FLUX.1-Fill-dev`, `-Depth-dev`, `-Canny-dev` (+ `-lora`), `-Redux-dev` | FLUX.1 [dev] NC (Hub tag `other`) | Flux Fill/Control pipelines **[U]** | Structure-conditioned FLUX.1 tools |
| `black-forest-labs/FLUX.1-schnell` | Apache-2.0 | `FluxPipeline` | T2I only |

Licence detail, FLUX.1 [dev] NC ([LICENSE.md](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/blob/main/LICENSE.md)) **[V]**:

- Outputs: "We claim no ownership rights in and to the Outputs." "You may use Output for any purpose (including for commercial purposes), except as expressly prohibited herein."
- Outputs may not be used to train a model competitive with FLUX.1 [dev].
- Model use must be non-commercial; the definition excludes use "in direct interactions with or that has impact on end users". Whether batch-generating tiles for a public website falls outside that is **a legal question we have not resolved**.
- Must use content filters or review outputs before distribution, and disclose AI generation "to the extent required under applicable law".

FLUX 3 Kommunity licence: "non-commercial use, plus commercial output generation by Qualifying Users" (under US$5M revenue) — card summary only; licence text not read **[U]**. FLUX.2 Non-Commercial licence text not read; the FLUX.2-dev card repeats the "outputs can be used for personal, scientific, and commercial purposes" line **[V]** (card), licence text **[U]**.

FLUX.2 klein inpainting in Diffusers: `Flux2KleinInpaintPipeline` takes `image`, `mask_image`, `strength` (0.8), and **`image_reference`** ("to be used as the reference for the masked area"), with the same per-step latent mask blend. Docstring example uses `FLUX.2-klein-base-9B`, default 50 steps, `guidance_scale` 8.0 ([source](https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/flux2/pipeline_flux2_klein_inpaint.py)) **[V]**. This is the only verified Diffusers pipeline that combines a hard mask with a separate reference image. Use with the Apache `-base-4B` weights is **[U]**.

FLUX ControlNets ([Hub search](https://huggingface.co/api/models?search=FLUX.2+controlnet&sort=downloads&direction=-1&limit=20)) **[V]**: `Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0` and `alibaba-pai/FLUX.2-dev-Fun-Controlnet-Union`, both licence `other` and tied to non-commercial bases. No ControlNet for the Apache klein 4B was found.

### 2.2 SDXL + ControlNet + pixel-art LoRA

- Base `stabilityai/stable-diffusion-xl-base-1.0`: CreativeML Open RAIL++-M **[U]** (not re-read today).
- `xinsir/controlnet-tile-sdxl-1.0`: Apache-2.0 ([card](https://huggingface.co/xinsir/controlnet-tile-sdxl-1.0)) **[3P/V via search]**. Union ControlNets load through `ControlNetUnionModel` (Diffusers community README example) **[V]**.
- Pixel-art LoRA: `nerijs/pixel-art-xl`, `creativeml-openrail-m`, 39k downloads ([Hub search](https://huggingface.co/api/models?search=pixel-art+xl&sort=downloads&direction=-1&limit=12)) **[V]**.
- VRAM about 8–12 GB, runs on MPS **[U]**.
- Most mature in Diffusers: core inpaint/img2img/ControlNet pipelines plus community tiled pipelines `mixture_tiling_sdxl` and `mod_controlnet_tile_sr_sdxl` ([community README](https://github.com/huggingface/diffusers/blob/main/examples/community/README.md)) **[V]**.
- Weakness: older, weaker instruction following; quality relies on ControlNet strength. Still the only stack where true tiled diffusion is available off the shelf.

### 2.3 Other open-weights editors released in 2026

Artificial Analysis open-weights editing leaderboard, read 2026-11-15 ([source](https://artificialanalysis.ai/image/leaderboard/editing/open-weights)) **[V]** as a listing; Elo is crowd preference on general edits, **not** geometry fidelity:

| Rank | Model | Released | Licence | Status for us |
|---|---|---|---|---|
| 1 | MiniMax H3-Image (`MiniMaxAI/MiniMax-H3-Image`) | 2026-11 | `other`, card gated (401) | Unverified; library `minimax-h3`, not Diffusers ([Hub](https://huggingface.co/api/models?author=MiniMaxAI&search=H3&limit=10)) |
| 2 | Bria Fibo 2.0 | 2026-10 | not checked **[U]** | Diffusers dir `bria_fibo2` exists |
| 3 | Qwen-Image-2.1 | 2026-09 | Qwen Research (non-commercial) | Excluded on licence |
| 4 | FLUX 3 Image Klein | 2026-10 | FLUX Kommunity | Restrictive; 31 GB |
| 5 | HunyuanImage 3.0 Instruct | 2026-01 | not checked **[U]** | — |
| 6 | FLUX.2 klein 9B | 2026-01 | FLUX NC | Excluded on licence |
| 10 | Qwen Image Edit Plus 2511 | 2025-11/12 | Apache-2.0 | **Primary** |
| 12 | HiDream-O1-Image | 2026-05 | reported MIT **[3P]** | Not investigated |
| 13 | FLUX.2 klein 4B | 2026-01 | Apache-2.0 | **Fallback** |

Also seen:

- `FireRedTeam/FireRed-Image-Edit-1.0` — Apache-2.0, 20B, loads with `QwenImageEditPlusPipeline`, multi-image ([card](https://huggingface.co/FireRedTeam/FireRed-Image-Edit-1.0)) **[V]**. Drop-in A/B candidate for the primary at zero integration cost.
- `Boogu/Boogu-Image-0.1-Edit` — Apache-2.0, 10B, released 2026-06-16, 25–50 steps; official inference is the project's own script, no Diffusers dir (read from a mirror card: [mirror](https://huggingface.co/vicentecarro/Boogu-Image-0.1-Edit)) **[3P]**.
- Diffusers `main` also has `krea2`, `joyimage`, `longcat_image`, `glm_image`, `z_image`, `hidream_image` directories ([source](https://github.com/huggingface/diffusers/tree/main/src/diffusers/pipelines)) **[V]** — not investigated.

### 2.4 Comparison table

| Model | Licence | Can outputs go on a public site under an open licence? | Conditioning | VRAM | Steps | Diffusers maturity |
|---|---|---|---|---|---|---|
| `Qwen/Qwen-Image-Edit-2511` | Apache-2.0 | Yes: no output restriction in Apache-2.0 | Image list (soft), LoRA; mask only via `QwenImageEditInpaintPipeline` [U for 2511] | 40 GB+ BF16; 13–22 GB quantised | 40 (4 w/ Lightning) | Core pipeline, released |
| `FireRedTeam/FireRed-Image-Edit-1.0` | Apache-2.0 | Yes | Same as above | Same class (20B) | n/s | Reuses Qwen Edit Plus |
| `black-forest-labs/FLUX.2-klein-4B` / `-base-4B` | Apache-2.0 | Yes | Multi-reference; mask + `image_reference` inpaint; LoRA | ~13 GB | 4 (base: 50) | Core pipelines on `main` |
| `black-forest-labs/FLUX.2-klein-9B` | FLUX NC | Outputs probably yes, model use must be non-commercial; unresolved | Same as 4B | ~29 GB | 4 | Core |
| `black-forest-labs/FLUX.2-dev` | FLUX NC | As above | Multi-reference, Fun ControlNet union | 32B; 4-bit variant exists | 28–50 | Core |
| `black-forest-labs/flux-3-image-klein` | FLUX Kommunity | Likely for small entities; licence unread | Up to 10 refs, bounding boxes | 25–31 GB (+28 GB upsampler) | 16 | Modular only, `main` |
| `black-forest-labs/FLUX.1-Kontext-dev` | FLUX.1 [dev] NC | Outputs: "any purpose"; model use NC; unresolved | One image; community multi-image pipeline | ~24 GB class [U] | ~28 [U] | Core, mature |
| FLUX.1 Fill/Depth/Canny dev | FLUX.1 [dev] NC | As Kontext | Mask / depth / canny | ~24 GB class [U] | ~28–50 [U] | Core, mature |
| `Qwen/Qwen-Image-2.1` | Qwen Research | **No clear right**; research/evaluation only | Up to 10 refs, masks, Fun ControlNet | n/s (7B) | 40 | Core on `main` |
| SDXL + `xinsir` ControlNets + `nerijs/pixel-art-xl` | OpenRAIL++-M [U] / Apache-2.0 / OpenRAIL-M | Yes, subject to OpenRAIL use restrictions [U] | Depth, canny, tile, inpaint, LoRA, tiled diffusion | 8–12 GB [U] | 20–35 | Most mature |
| `MiniMaxAI/MiniMax-H3-Image` | `other`, unread | Unknown | Unknown | Unknown | Unknown | Not in Diffusers |

n/s = not stated on the source.

---

## 3. Seam consistency across tiles

### 3.1 What Isometric NYC actually did

From the author's write-up ([source](https://cannoneyed.com/projects/isometric-nyc)) **[V]**:

- Nano Banana first; style consistency poor.
- Production model: a **fine-tuned** Qwen Image Edit, about 40 pairs.
- Schema of 512×512 "quadrants", "with a given model call generating a 2x2 quadrant image from an input with a mask."
- Infill training data: "input images that have a certain percentage of the target generated image 'masked' out."
- Rule: "no quadrant may be generated such that a 'seam' will be present."
- Failures remained: "the model still demonstrated a number of failure modes (especially around water and terrain)"; "I couldn't get them to reliably generate water"; trees were a pathological case.
- QA stayed manual: "I had to give up on fully automated generation because the models simply couldn't understand their own mistakes."
- Throughput on a Lambda H100: "For less than $3 an hour and more than 200 generations/hour"; about 40k tiles estimated.

The article does not say whether the input was one composite image or several images, nor how the masked region was drawn. Our reading (one composite) is an inference **[U]**.

### 3.2 Techniques and what Diffusers supports today

| Technique | How it works | Qwen-Edit-2511 | FLUX.2 klein 4B | SDXL |
|---|---|---|---|---|
| A. Neighbour-conditioned infill, single composite | Paste already-styled neighbour pixels and the raw render for the missing part into one input; ask the model to finish; paste known pixels back | Works with `QwenImageEditPlusPipeline` as plain image-in/image-out. Zero-shot compliance not shown by any source; NYC needed a LoRA | Same, via `Flux2KleinPipeline` | Not instruction-driven |
| B. Hard-masked inpaint | Known region re-imposed in latent space each step | `QwenImageEditInpaintPipeline` (verified for `Qwen-Image-Edit`; 2511 [U]) | `Flux2KleinInpaintPipeline` with `image_reference` (base-9B example; base-4B [U]) | Core SDXL inpaint + ControlNet, mature |
| C. Overlapping tiles + masked blending | Generate with margin, feather or cut along low-gradient paths in post | Model-agnostic, pure post-processing | Same | Same |
| D. Tiled diffusion (MultiDiffusion / Mixture of Diffusers) | Average overlapping denoising windows every step | **Not available** for Qwen in Diffusers | **Not available** | `mixture_tiling_sdxl`, `mod_controlnet_tile_sr_sdxl` community pipelines [V]; core `StableDiffusionPanoramaPipeline` (SD1.5) [U] |
| E. Reference-image conditioning | Pass style/neighbour tiles as extra images | Image list, sequence-concatenated | Multi-reference | IP-Adapter [U] |

### 3.3 What the sources do and do not support

- **Multi-image conditioning does not guarantee seamless or geometry-faithful output.** In the Edit Plus pipeline, references are resized to about 1 MP and attended to as extra tokens; there is no spatial lock (section 1.3). No model card claims seam continuity or pixel-accurate structure preservation. The 2511 card claims reduced "image drift", which is a relative improvement, not a guarantee.
- The only public project doing this at scale needed a fine-tune and still had residual failures and manual correction (3.1).
- Hard masking (B) guarantees that **known pixels are unchanged**; it does not guarantee that new content meets them without a visible style or geometry jump. The latent-resolution mask also softens the boundary.
- Tiled diffusion (D) gives real cross-tile consistency during sampling, but exists off the shelf only for SD1.5/SDXL.
- A VAE round trip alters pixels slightly even in "preserved" regions; always paste original known pixels back in pixel space. This is standard practice, stated here as engineering judgement **[U]**.

Our structural advantage over Isometric NYC: the input is a clean procedural render with an exact building-ID mask and a depth buffer, so geometry drift is measurable automatically (section 4), and palette quantisation hides small colour mismatches at seams.

---

## 4. Post-processing and automated QA

These are design proposals built on stable library functions; none was run today **[U]**.

### 4.1 Enforcing pixel art

1. Generate at 1024² (or with overlap margin).
2. Downscale by an integer factor with nearest-neighbour or box filter (`PIL.Image.resize(..., Image.NEAREST)` / `Image.BOX`). Box then quantise is usually cleaner than nearest on AI output.
3. Quantise to a **fixed project palette** (`Image.quantize(palette=pal_img, dither=Image.Dither.NONE)`). One global palette for the whole map, not per tile, or seams reappear as palette shifts.
4. Optionally upscale back with nearest-neighbour for display.
5. Paste protected layers (labels, building outlines from the procedural render) on top if fidelity matters more than style.

### 4.2 Structural-fidelity metrics

| Metric | Definition | Suggested go threshold (to calibrate) |
|---|---|---|
| Edge IoU / boundary F-score | Canny edges of output vs boundaries of the building-ID mask, both dilated by 2 px at 1024² | Boundary recall ≥ 0.80 |
| Edge SSIM | `skimage.metrics.structural_similarity` between Sobel magnitude of procedural render and of output | ≥ 0.60 |
| Per-building colour separability | Mean colour inside each building-ID region vs its neighbours; detects merged or vanished buildings | ≥ 95% of buildings distinguishable |
| Palette distance | Mean ΔE (Oklab or CIEDE2000) from each pre-quantisation pixel to nearest palette colour | Report only; lower is better |
| Seam score | Mean abs difference across the tile boundary divided by the same statistic on interior lines | Ratio ≤ 1.3 |
| Known-pixel drift | Max abs difference in the preserved region before paste-back | Report only |

Always compute the same metrics on the **baseline**: procedural render → downscale → palette quantise, with no model. If the baseline looks acceptable to the owner, the AI step may not be needed at all.

Thresholds are starting points; calibrate on 3–5 hand-judged tiles before the run. Automated metrics do not replace human review: Isometric NYC found model-based QA unreliable (3.1).

---

## 5. Costs (volatile — read 2026-11-15)

Prices change weekly. Re-check before spending. USD as published; EUR conversion not checked **[U]**.

### 5.1 GPU rental, on-demand, per hour

| Provider | 24 GB | 48 GB | 80 GB | Source |
|---|---|---|---|---|
| RunPod Secure | RTX 3090 $0.50; RTX 4090 $0.89; A5000 $0.27; L4 $0.69 | A6000 $0.69; A40 $0.59; L40S $1.09; 6000 Ada $1.09 | A100 PCIe $2.09; H100 PCIe $2.89 | [runpod.io/pricing](https://www.runpod.io/pricing) [V] |
| RunPod Community | RTX 3090 $0.22; RTX 4090 $0.34; A5000 $0.16 | A6000 $0.33; A40 $0.35; L40S $0.79 | A100 PCIe $1.19; H100 PCIe $1.99 | same [V] |
| Lambda | Quadro RTX 6000 $0.69; A10 $1.29 | A6000 $1.09 | H100 PCIe $3.79 (A100 is 40 GB at $1.99) | [lambda.com/pricing](https://lambda.com/pricing) [V] — page says these take effect 2026-11-16 00:00 UTC |
| Vast.ai | RTX 4090 about $0.20–0.70 | A6000 about $0.36–0.52 | — | Marketplace; official page showed no figures. Aggregators only [3P]: [getdeploying](https://getdeploying.com/gpus/nvidia-a6000), [vast.ai/pricing](https://vast.ai/pricing) |

RunPod also lists RTX 5090 32 GB at $1.39 secure / $0.69 community **[V]**.

### 5.2 Hosted per-image prices

| Service | Model | Price | Source |
|---|---|---|---|
| fal.ai | `fal-ai/qwen-image-edit-2511` | "$0.03 per megapixel" | [fal page](https://fal.ai/models/fal-ai/qwen-image-edit-2511) [V] |
| fal.ai | FLUX.2 klein 4B edit | "$0.01 per megapixel" | [fal page](https://fal.ai/models/fal-ai/flux-2/klein/4b/edit) [V] |
| Replicate | `qwen/qwen-image-edit-2511` | Not shown on the page fetched | [model page](https://replicate.com/qwen/qwen-image-edit-2511) [U] |
| Replicate | Hardware billing | L40S $0.000975/s; A100 80 GB $0.0014/s | [replicate.com/pricing](https://replicate.com/pricing) [V] |
| Alibaba Model Studio (Singapore) | `qwen-image-edit` | $0.045/image | [official doc](https://www.alibabacloud.com/help/en/model-studio/model-qwen-image-edit) via search summary [3P] |
| Alibaba Model Studio | `qwen-image-edit-plus` | $0.03/image | Third-party table only [3P]: [invideo](https://invideo.io/blog/qwen-image-ai-generator/) |
| Alibaba Model Studio | `qwen-image-2.1-turbo` / `-pro` | $0.016 / $0.04 per image | [Alibaba Cloud blog](https://www.alibabacloud.com/blog/qwen-image-2-1-pro-and-turbo-apis-are-live-one-7b-model-to-generate-edit-and-cut-out_603679) via search summary [3P] |

Whether fal bills input megapixels as well as output was not checked **[U]**. Hosted APIs give no control over revision hash and limited control over scheduler, which weakens provenance (section 6); hosted LoRA inference pricing was not found.

---

## 6. Licence, ethics, provenance

### 6.1 Restrictions on published artwork

- **Apache-2.0 models (Qwen-Image-Edit, -2509, -2511; FireRed; FLUX.2 klein 4B; Lightning LoRA):** the licence covers the software/weights and places no restriction on outputs. We may publish tiles under an open licence. Whether purely AI-generated imagery is copyrightable at all varies by jurisdiction and is outside this document; in our case the tiles are derived from our own procedural render **[U]** (not legal advice).
- **FLUX non-commercial family:** outputs are usable "for any purpose" under FLUX.1 [dev] NC, but model *use* must be non-commercial, filters/manual review are mandatory, and BFL says it may contact deployers to verify ([Kontext card](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev)) **[V]**. Avoid unless the Apache options fail.
- **Qwen Research License (Qwen-Image-2.1):** research/evaluation only. Avoid.
- **LoRAs and ControlNets carry their own licences** (`nerijs/pixel-art-xl` is OpenRAIL-M; community LoRAs vary — one 2511 4-bit repack is CC-BY-NC-SA). Check each adapter before use.
- **Input data licences still apply.** Restyling does not remove OpenStreetMap ODbL attribution or cadastral data terms; see the geodata research documents.
- **Disclosure.** Label the restyled layer as AI-assisted on the site and in the README. The EU AI Act Article 50 transparency duties are relevant to AI-generated content; exact applicability to stylised map tiles was not researched **[U]**.
- **Style ethics.** Use generic style prompts ("isometric pixel art, limited palette"); do not prompt with living artists' names or train a LoRA on artwork we do not have rights to. If a LoRA is trained, train it on pairs we produce ourselves.

### 6.2 Provenance record (one JSON line per generated tile)

- Model repo ID **and commit SHA** (`revision=`), for base model, text encoder, VAE, every LoRA/ControlNet, with LoRA weight filename and scale.
- Quantisation variant (BF16 / FP8 / GGUF Qx / bnb-4bit) and file hash.
- Library versions: `diffusers` (commit if installed from `main`), `torch`, `transformers`; GPU model; dtype.
- Pipeline class, scheduler class and config, steps, `true_cfg_scale` / `guidance_scale`, `strength`, width, height.
- Seed and generator device.
- Prompt and negative prompt, verbatim.
- SHA-256 of every input image (procedural render, building-ID mask, neighbour tiles, composite input, mask).
- SHA-256 of raw output and of the post-processed tile; palette file hash; post-processing parameters.
- Attempt number, QA metric values, human accept/reject, reviewer, timestamp.
- For hosted APIs: provider, endpoint, request ID, date (revision is not controllable).

Keep raw outputs; never overwrite. BFL's API adds C2PA metadata; the open weights do not ([FLUX.2 klein card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)) **[V]**. Writing our own provenance into PNG text chunks or a sidecar file is enough.

---

## 7. Recommended benchmark design

### 7.1 Choices

- **Primary:** `Qwen/Qwen-Image-Edit-2511`, Apache-2.0, `QwenImageEditPlusPipeline`. Reasons: permissive licence, released Diffusers pipeline, largest ecosystem (GGUF, Lightning, LoRA trainers), and the only family with a public precedent for exactly this task.
- **Fallback:** `black-forest-labs/FLUX.2-klein-4B` (distilled, 4 steps, ~13 GB) for restyle and composite infill, with `FLUX.2-klein-base-4B` for hard-masked inpaint (`Flux2KleinInpaintPipeline` + `image_reference`) and any LoRA. Both Apache-2.0. Reasons: fits a 24 GB card or possibly a Mac, cheapest per image, and has the only verified mask + reference pipeline.
- **Free A/B if time allows:** `FireRedTeam/FireRed-Image-Edit-1.0` through the same Qwen pipeline code.
- **Control:** no model — procedural render, downscale, palette quantise.

### 7.2 Technique

1. **Stage 0 — single-tile restyle (geometry test).** Procedural render in, restyled tile out, one image, fixed prompt, fixed seed set. Measures fidelity only.
2. **Stage 1 — neighbour-conditioned infill, single composite.** 1024² canvas in 512² quadrants. Known quadrants hold accepted styled output; unknown quadrants hold the raw render. Prompt asks to complete in the same style. Layouts: 1 of 4 known, 2 of 4 (edge), 3 of 4 (corner). Paste known pixels back in pixel space, then quantise. Optionally add one accepted tile as a second image for style reference.
3. **Stage 1b — hard mask** with `QwenImageEditInpaintPipeline` (or the FLUX.2 klein inpaint pipeline) on the same layouts, if Stage 1 alters known quadrants or leaves visible joins.
4. **Stage 2 — LoRA, only if Stage 0 passes and Stage 1 fails on seams.** About 40 pairs built from hand-approved Stage 0/1 outputs, masked-infill format as in Isometric NYC. Requires separate owner approval.

Tile set: 10–25 tiles chosen to cover dense old town, regular blocks, the castle hill, industrial sheds, fields/trees, and any water. Trees and water were the failure cases in the precedent.

### 7.3 Hardware

- Default: **one RunPod A6000/A40 48 GB pod** ($0.33–0.69/h) with BF16 transformer on GPU and `enable_model_cpu_offload()` for the text encoder; or GGUF Q8 (22.4 GB) to avoid offload thrash.
- Faster and simpler: **A100 80 GB** ($1.19–2.19/h), everything on GPU.
- Fallback model: any 24 GB card ($0.16–0.89/h).
- Zero-setup alternative for Stage 0–1 only: fal.ai endpoints, at the cost of weaker provenance and no hard-mask pipeline.

### 7.4 Cost estimate: 25 tiles × about 4 attempts = 100 generations

| Item | Assumption | Cost |
|---|---|---|
| Primary, self-hosted, 48 GB | 100 images × up to ~3 min at 40 steps ≈ 5 h, plus ~3 h download/setup/debug = 8 h × $0.69 | about $6 |
| Primary, self-hosted, A100 80 GB | 8 h × $2.19 | about $18 |
| Primary via fal.ai | 100 × ~1 MP × $0.03 | about $3 |
| Fallback (klein 4B), 24 GB pod | 3 h × $0.89 | about $3 |
| Fallback via fal.ai | 100 × $0.01 | about $1 |
| Storage/egress, mistakes, reruns | ×2 contingency | — |
| **Stages 0–1, both models, with contingency** | | **about $25–50** |
| Optional Stage 2 LoRA | Precedent ~$12 for ~4 h; budget 8 h on 48–80 GB | about $10–20 |
| **Whole benchmark, upper bound** | | **about $60–70 (under half the €150 cap)** |

Time per image is the least certain input (section 1.8). Measure it on the first 3 images and stop if the projection exceeds the approved amount.

### 7.5 Go / no-go criteria

Go to a larger pilot only if all hold on the primary or the fallback:

1. **Geometry:** at least 80% of tiles pass the edge thresholds in 4.2 within 4 attempts, and no accepted tile has an invented, missing or merged building on human inspection.
2. **Seams:** at least 80% of Stage 1 joins have seam ratio ≤ 1.3 after quantisation and are not visible to a human at display zoom.
3. **Style:** a 5×5 mosaic looks like one drawing; the owner prefers it to the no-model control in a side-by-side.
4. **Yield and cost:** mean attempts per accepted tile ≤ 2.5, and projected full-map cost (tiles × attempts × measured cost) is within a budget the owner accepts.
5. **Licence and provenance:** every component is Apache-2.0 (or otherwise cleared) and every accepted tile has a complete provenance record.

No-go, and stay procedural, if: the control is judged as good or better; geometry fails on more than 20% of tiles on both models; seams need manual repair on more than 20% of joins even with hard masking; or success depends on a non-commercial or research-only model.

Middle outcome: Stage 0 passes but seams fail → ask approval for Stage 2 (LoRA), or restrict AI restyling to isolated sprites (landmarks, trees) composited onto the procedural map, where seams do not exist.

---

## 8. Not verified / unresolved

Licences and legal:

- Full text of the FLUX Non-Commercial License (FLUX.2) and FLUX Kommunity License v1.0 not read; only card summaries.
- Whether generating tiles for a public, non-monetised website is "non-commercial" under BFL licences ("direct interactions with or … impact on end users").
- Licence and capabilities of `MiniMaxAI/MiniMax-H3-Image` (card returned 401), Bria Fibo 2.0, HunyuanImage 3.0 Instruct, HiDream-O1 (reported MIT by a third party).
- SDXL base licence text not re-read today.
- Copyright status of AI-restyled tiles and EU AI Act Article 50 applicability.
- `FLUX.2-klein-base-4B` card not read (Apache-2.0 from Hub tag only).

Capabilities:

- Whether `QwenImageEditInpaintPipeline` works correctly with `-2509`/`-2511` weights.
- Whether `Flux2KleinInpaintPipeline` works with the Apache 4B base weights (example uses base-9B).
- Recommended maximum number of input images for Edit-2509/2511 ("1–3" is from memory).
- Qwen-Image-Edit-2511 behaviour above ~1 MP.
- GGUF loading of the Qwen transformer in Diffusers; first-party Diffusers LoRA training script for Qwen edit.
- Whether Isometric NYC used a single composite input and how its mask was drawn.
- Core `StableDiffusionPanoramaPipeline` (MultiDiffusion) current status.
- Qwen text-encoder size (~16 GB) and parameter count of the edit transformer (20B inferred from file size and the FireRed card).

Performance:

- No first-hand or like-for-like VRAM/speed numbers for 2511 (BF16, GGUF, Lightning) on 24/48 GB cards. All figures in 1.8 are third-party and partly for older variants.
- Apple Silicon: MLX conversions exist, but no RAM or speed data. MPS for FLUX.2 klein untested.
- Quality of the 4-step Lightning LoRA for structure-preserving restyling.
- **No source demonstrates zero-shot seamless, geometry-faithful tile restyling with any candidate.** This is the question the benchmark exists to answer.

Prices:

- Vast.ai figures are aggregator ranges, not from Vast.
- Replicate per-run price for Qwen-Image-Edit-2511 not found.
- Alibaba Model Studio prices came through search summaries, not a page read in full.
- fal.ai input-megapixel billing and hosted LoRA pricing.
- Lambda prices shown take effect 2026-11-16.
- USD→EUR rate not checked.
