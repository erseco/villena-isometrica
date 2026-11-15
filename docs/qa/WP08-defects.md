# WP08 defect list

Defects found by the cross-component tests. Each strict `xfail` in the suite maps to exactly one entry here.
Product code was not changed; owners fix them. Run `uv run --project pipeline pytest tests/integration -q --runxfail`
to see each one fail.

| ID | Severity | Test | Owner |
|---|---|---|---|
| WP08-D-01 | minor | `tests/integration/test_failures.py::test_renderer_polygon_with_fewer_than_four_coordinates` | WP04 (renderer input validation) |

## WP08-D-01: the renderer accepts a polygon ring with fewer than 4 positions

- **Evidence.** Copy `tests/fixtures/scene-synthetic`, cut the exterior ring of `syn-001_1` in `buildings.geojson` to its
  first 3 positions, put the new sha256 of the file in `scene.json`, then run
  `bun run render --scene <copy> --city tests/fixtures/city-synthetic/city.json --out <out>`.
  Result: exit status 0, `rendered 726x481 px, 6 parts, 3 trees`, no warning. A closed ring needs at least 4 positions
  (RFC 7946 section 3.1.6; scene.md: "Polygons are valid").
- **Expected.** Exit status 1 and a message naming `buildings.geojson` and the feature id, like the other input errors
  of `pipeline/rendering/src/scene.ts` (wrong sha256, wrong terrain length, schemaVersion 2.0, NaN: all pass).
- **Impact.** Low for the real pipeline, because the GIS stage emits valid rings (`make_valid`, CCW, explode). A
  hand-edited or foreign scene would render a degenerate building silently instead of failing.
- **Fix.** Check `ring.length >= 4` and first == last for every ring when loading a layer.

## Not defects, but worth a decision (no xfail)

- **O-1: "a background pixel has no pick" is stricter in render.md section 3 than in projection.md 5.2.** The viewer
  implements 5.2 faithfully: *no pick* means the pixel's ray never enters the height grid. The grid covers the AOI plus
  `marginM` (8 m in the fixture, 32 px), while the renderer draws only the AOI prism. So the strip of background
  around the drawn diamond is picked as margin ground and does update the URL. Only pixels farther out (image
  corners, about a quarter of the image at Villena) have no pick. Observed while writing the e2e test: with the
  viewport centre at image X ~ 330 (just outside the AOI tip at (363, 470)) the URL changed; at X < 200 it did not.
  The e2e test therefore uses the second case, which both readings agree on. The contract owner should say which
  reading is intended; if "every background pixel", the viewer must also test the class of the pixel or the exporter
  must publish the AOI rectangle with the grid.
