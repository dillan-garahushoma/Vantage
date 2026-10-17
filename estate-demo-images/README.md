# Valora Estate Demo Images

This directory contains AI-generated property assets created for **Valora**, a South African residential estate management and property-health platform.

All images are generated as photorealistic, 16:9 landscape architectural photographs tailored specifically to South African residential estate vernacular, environmental lighting, native flora (fever trees, agapanthus, strelitzia, aloes), perimeter security infrastructure, and distinct maintenance condition tiers.

---

## Portfolio Overview & Maintenance Tiers

| Estate | Typology & Maintenance Profile | Target Condition |
| :--- | :--- | :--- |
| **Silverleaf Reserve** | Premium gated luxury estate | Exceptional, immaculate maintenance & security |
| **Willowbrook Mews** | Middle-market townhouse complex | Well-managed, clean, practical, modest |
| **Lakeside Gardens** | Established mature residential complex | Inconsistent, mixed performance, ageing infrastructure |
| **Eastbank Court** | Ageing multi-storey walk-up block | Poorly managed, noticeable deferred maintenance backlogs |
| **Quarry View Flats** | High-density urban walk-up block | Serious operational stress, accumulated neglect |

---

## Asset Manifest & Status

| # | Filename | Estate | Role | Status | Description |
|---|---|---|---|---|---|
| 01 | `silverleaf-reserve-01-hero.jpg` | Silverleaf Reserve | Hero / Exterior | **Generated & Verified** | Elevated landscape view of contemporary luxury homes with charcoal standing seam roofs, sandstone cladding, timber pergolas, lush indigenous gardens, fever trees, and pristine internal asphalt/paved road. |
| 02 | `silverleaf-reserve-02-entrance.jpg` | Silverleaf Reserve | Entrance / Security | **Generated & Verified** | Dual-lane secure gatehouse matching estate architecture, boom gates, stone boundary walls, neat pavers, fever trees, aloes, and clear daytime lighting. |
| 03 | `silverleaf-reserve-03-amenities.jpg` | Silverleaf Reserve | Amenities | **Generated & Verified** | Resident clubhouse with expansive slatted timber pergola deck, designer sun loungers, sparkling blue lap pool, manicured lawn, and Cape mountain backdrop. |
| 04 | `silverleaf-reserve-04-infrastructure.jpg` | Silverleaf Reserve | Infrastructure | **Generated & Verified** | Paved curved pedestrian walkway, minimalist dark bollard path lighting, flush service utility access covers, manicured indigenous verge, and pristine roadway curbs. |
| 05 | `willowbrook-mews-01-hero.jpg` | Willowbrook Mews | Hero / Exterior | **Generated & Verified** | Neat two-storey greige duplex townhouses with charcoal concrete roof tiles, tidy lawns, paved patios, interlocking brick driveway, and perimeter wall with electric fencing. |
| 06 | `willowbrook-mews-02-entrance.jpg` | Willowbrook Mews | Entrance / Security | *Pending Quota Reset* | Motorized charcoal steel sliding security gate, pedestrian gate, compact guardhouse in matching greige plaster, intercom pedestal, and strelitzia garden bed. |
| 07 | `willowbrook-mews-03-amenities.jpg` | Willowbrook Mews | Amenities | *Pending Quota Reset* | Neat communal lawn courtyard with simple timber pergola, paved pathway, and modest outdoor benches for resident use. |
| 08 | `willowbrook-mews-04-infrastructure.jpg` | Willowbrook Mews | Infrastructure | *Pending Quota Reset* | Orderly carport parking bays, clear bay numbering, painted speed bumps on interlocking brick paving, and tidy brick refuse enclosure. |
| 09 | `lakeside-gardens-01-hero.jpg` | Lakeside Gardens | Hero / Exterior | *Pending Quota Reset* | Established 1990s face-brick and plastered townhouse complex with mature shade trees, communal lawn near a small lake/pond, showing functional age. |
| 10 | `lakeside-gardens-02-entrance.jpg` | Lakeside Gardens | Entrance / Security | *Pending Quota Reset* | Dated automated sliding gate with slightly faded paint, older brick guard booth, weathered asphalt/patched paving, functional intercom, and mature creepers. |
| 11 | `lakeside-gardens-03-amenities.jpg` | Lakeside Gardens | Amenities | *Pending Quota Reset* | Communal garden with mature weeping willows/acacias, older communal swimming pool with clean water but weathered brick surround, and concrete picnic bench. |
| 12 | `lakeside-gardens-04-infrastructure.jpg` | Lakeside Gardens | Infrastructure | *Pending Quota Reset* | Tarmac driveway showing minor asphalt patching, communal carports with slightly weathered corrugated iron roofing, and functional but dated exterior fixtures. |
| 13 | `eastbank-court-01-hero.jpg` | Eastbank Court | Hero / Exterior | *Pending Quota Reset* | Ageing 3-4 storey walk-up apartment blocks with weathered cream/ochre painted plaster, water stains, worn asphalt open parking lot, and patchy neglected lawn. |
| 14 | `eastbank-court-02-entrance.jpg` | Eastbank Court | Entrance / Security | *Pending Quota Reset* | Worn entrance with tired boundary wall, peeling paint, dated manual/automated steel gate with surface wear, outdated intercom panel, and cracked asphalt. |
| 15 | `eastbank-court-03-amenities.jpg` | Eastbank Court | Amenities | *Pending Quota Reset* | Neglected communal courtyard with patchy dry grass, overgrown shrubbery, cracked concrete walkway, and weathered communal bench/clotheslines. |
| 16 | `eastbank-court-04-infrastructure.jpg` | Eastbank Court | Infrastructure | *Pending Quota Reset* | Visible deferred maintenance: cracked non-structural plaster, peeling paint, weathered exterior downpipe with staining, and cracked paving with weed intrusion. |
| 17 | `quarry-view-flats-01-hero.jpg` | Quarry View Flats | Hero / Exterior | *Pending Quota Reset* | Dense utilitarian 3-storey walk-up apartment blocks with external access corridors, weathered concrete/ochre plaster, corrugated carports, and coarse grass. |
| 18 | `quarry-view-flats-02-entrance.jpg` | Quarry View Flats | Entrance / Security | *Pending Quota Reset* | High precast concrete wall (stop-nonsense walling) with faded paint, heavy weathered steel sliding gate, worn gravel/broken asphalt apron, and basic access box. |
| 19 | `quarry-view-flats-03-amenities.jpg` | Quarry View Flats | Amenities | *Pending Quota Reset* | Open shared yard between blocks with hard-packed dirt, sparse grass tufts, simple concrete clothesline poles, and worn metal bench. |
| 20 | `quarry-view-flats-04-infrastructure.jpg` | Quarry View Flats | Infrastructure | *Pending Quota Reset* | Weathered external concrete stairwell and walkways, stained facade, cracked open concrete stormwater drainage channel, and scuffed common property finishes. |

---

## Technical Generation Notes & Upstream Limitation

### Generation Tooling
Assets are generated via Google Cloud's `gemini-3.1-flash-image` model through the IDE's image-generation agent workflow.

### Upstream Service Quota Status
During generation of asset 06 (`willowbrook-mews-02-entrance.jpg`), the upstream model service returned:
```json
{
  "code": 429,
  "message": "You have exhausted your capacity on this model. Your quota will reset after 167h40m9s.",
  "status": "RESOURCE_EXHAUSTED",
  "reason": "QUOTA_EXHAUSTED",
  "domain": "cloudcode-pa.googleapis.com",
  "metadata": {
    "model": "gemini-3.1-flash-image",
    "quotaResetTimeStamp": "2026-10-20T20:17:40Z"
  }
}
```
In accordance with project guidelines:
1. All 5 successfully generated, verified assets are retained directly in this directory.
2. No placeholder, copied, or synthetic substitute files are injected.
3. Complete visual identities and prompts for the remaining 15 assets are preserved in this manifest and can be resumed once quota capacity refreshes.

### Ready-to-run prompts for the remaining 15

The prose above is the art direction. The **executable** specification is
[`../tmp/imagegen/estate-demo-images.prompts.jsonl`](../tmp/imagegen/estate-demo-images.prompts.jsonl)
— one JSON record per remaining asset, in exactly the schema already recorded in
`estate-demo-heroes.jsonl`:

```json
{"out": "willowbrook-mews-02-entrance.jpg", "size": "2048x1152", "quality": "high",
 "output_format": "jpeg", "output_compression": 90, "use_case": "photorealistic-natural",
 "prompt": "Asset type: …"}
```

The three hero prompts that were sent but produced no file (`lakeside-gardens-01-hero`,
`eastbank-court-01-hero`, `quarry-view-flats-01-hero`) are re-emitted **verbatim** from that
log rather than rewritten. The other twelve keep each estate's identity from its hero
prompt — same materials, palette, building age and maintenance condition — so the four
images in a set read as one complex. `tmp/imagegen/write_prompts.py` regenerates the file.

### Verification performed on the assets that exist

| Check | Result |
|---|---|
| Files present and correctly named | 5 of 20, all names matching the required list |
| Format / decodability | JPEG, RGB, decoded and `verify()`-passed via Pillow |
| Dimensions and aspect | 1376×768, ratio 1.792 (16:9), uniform across all five |
| File size | 911–1007 KB each — sufficient for large estate-profile use |
| Photo-like, not flat/synthetic | 22 526–26 784 unique colours, channel stddev 64.5–76.3 |
| No duplicated or reused frames | pairwise dHash distance 25–34 (identical = 0, near-duplicate < 6) |
| Collages | none — every file is a single 16:9 photograph |

Note: 2048×1152 was requested and the service returned **1376×768** (still 16:9).
