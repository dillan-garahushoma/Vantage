"""Write the 15 remaining estate-demo image prompts as one JSONL record each.

The schema matches the records already in `estate-demo-heroes.jsonl`, so a run
resumes with exactly the parameters the earlier attempt used. The three hero
prompts that were sent but never produced a file are re-emitted verbatim from
that log rather than rewritten.

Run from the repository root:  python tmp/imagegen/write_prompts.py
"""

import json
import os

TAIL = (
    " no people, no vehicles, no text, no readable signs, no logos, no watermarks,"
    " no landmark, no copied real property, no collage, no multi-panel composition."
)


def constraints(lead):
    return "Constraints: " + lead + TAIL


def record(out, prompt):
    return {
        "out": out,
        "size": "2048x1152",
        "quality": "high",
        "output_format": "jpeg",
        "output_compression": 90,
        "use_case": "photorealistic-natural",
        "prompt": prompt,
    }


with open("tmp/imagegen/estate-demo-heroes.jsonl", encoding="utf-8") as fh:
    already_sent = {json.loads(line)["out"]: json.loads(line)["prompt"] for line in fh if line.strip()}


def house(estate, role, scene, subject, style, framing):
    """One prompt, in the shape every recorded prompt already uses."""
    return (
        f"Asset type: {role} for the estate directory. Primary request: {estate} "
        f"Scene/backdrop: {scene} Subject: {subject} Style/medium: {style} "
        f"Composition/framing: {framing}"
    )


# ----------------------------------------------------------------- Willowbrook
WILLOW = "the same original, fictional practical middle-market South African townhouse complex as the hero image."

willow_entrance = house(
    WILLOW,
    "estate-access photograph",
    "a functional single-lane vehicle entrance with a narrow pedestrian gate beside it, a compact "
    "plastered guardhouse in matching warm-grey plaster, and interlocking brick paving with a neat "
    "painted speed hump leading in.",
    "a charcoal motorised sliding gate in good working order, a simple intercom pedestal, a boundary "
    "wall topped with electric fencing, and tidy strelitzia and agapanthus beds against the wall.",
    "honest professional architectural real-estate photography, 35mm lens, soft natural morning light, "
    "realistic materials.",
    "wide 16:9 landscape from the road side, gatehouse and gate centred, residence roofs just visible "
    "beyond. " + constraints("clean, orderly and clearly secure rather than luxurious;"),
)

willow_amenities = house(
    WILLOW,
    "communal-amenities photograph",
    "a modest communal lawn courtyard between two rows of townhouses, bordered by a low brick wall and "
    "a compact paved gathering area.",
    "a simple slatted timber pergola over two plain benches and a small braai stand, clipped lawn, a "
    "young shade tree, and one small well-kept bed of agapanthus.",
    "honest professional architectural real-estate photography, 35mm lens, soft late-afternoon light.",
    "wide 16:9 landscape, courtyard in the foreground with townhouse facades framing it. "
    + constraints("modest, well maintained and believable, with no clubhouse, no pool and no gym;"),
)

willow_infra = house(
    WILLOW,
    "common-area condition photograph",
    "a paved parking court with painted bay lines and a shaded carport row, leading to a brick refuse "
    "enclosure with a clean bin area.",
    "interlocking brick paving in sound condition, a boundary wall with electric fencing, orderly "
    "external light fittings, a tidy meter and drain cover set, and clipped grass along the kerb.",
    "plain documentary architectural real-estate photography, 35mm lens, even natural daylight.",
    "wide 16:9 landscape looking along the parking court towards the carports and the refuse yard. "
    + constraints("in good repair and neatly kept, with nothing broken or neglected;"),
)

# ------------------------------------------------------------ Lakeside Gardens
LAKE = (
    "the same original, fictional established 1990s South African residential complex as the hero "
    "image: light-cream plaster with reddish face-brick sections, older brown tiled roofs."
)

lake_entrance = house(
    LAKE,
    "estate-access photograph",
    "a dated single-lane vehicle entrance with an older brick-faced guard booth and a patched asphalt "
    "apron, faded but legible lane markings, and a narrow pedestrian gate beside the boom.",
    "cream plaster and reddish face-brick matching the buildings, an older automated boom and intercom "
    "panel that still works, weathered concrete kerbing, mature creepers over part of the boundary "
    "wall, and one neatly clipped shrub bed beside a visibly untouched one.",
    "truthful professional architectural real-estate photography, 35mm lens, neutral overcast morning "
    "light, authentic minor weathering.",
    "wide 16:9 landscape from the road, entrance and booth centred, complex behind. "
    + constraints(
        "functional and occupied, somewhat dated and unevenly maintained, neither luxurious nor derelict;"
    ),
)

lake_amenities = house(
    LAKE,
    "communal-amenities photograph",
    "a communal garden beside a small ornamental pond, with an older rectangular swimming pool and a "
    "paved surround.",
    "clean but dated pool water, weathered brick paving with a few lifted edges, older concrete "
    "benches, mature weeping willows and acacias, a lawn that is mown but not manicured, and one "
    "overgrown corner where shrubs have been left.",
    "truthful professional architectural real-estate photography, 35mm lens, soft natural daylight.",
    "wide 16:9 landscape, pool and paved surround in the foreground, pond and mature trees behind. "
    + constraints("usable and clearly still in service, but inconsistently maintained;"),
)

lake_infra = house(
    LAKE,
    "common-area condition photograph",
    "a tarmac internal driveway between two blocks, with visible patch repairs, a row of older "
    "carports and a concrete stormwater kerb channel.",
    "a sound but aged surface, weathered corrugated carport roofing, older external light fittings of "
    "which one is conspicuously newer than the rest, thin grass along the kerb, and a tidy but clearly "
    "old utility box and meter bank.",
    "truthful documentary architectural real-estate photography, 35mm lens, flat natural daylight.",
    "wide 16:9 landscape along the driveway, carports to one side, blocks rising behind. "
    + constraints(
        "ageing and unevenly maintained, with patching and weathering but nothing broken or dangerous;"
    ),
)

# ---------------------------------------------------------------- Eastbank Court
EAST = (
    "the same original, fictional ageing 1970s South African apartment complex as the hero image: "
    "weathered pale beige and faded terracotta plaster with patchy repainting."
)

east_entrance = house(
    EAST,
    "estate-access photograph",
    "a worn single-lane entrance off a suburban road, with a tired boundary wall, faded painted kerbs "
    "and cracked asphalt at the apron.",
    "peeling pale beige paint over old plaster, a rust-stained steel sliding gate that still functions, "
    "an outdated intercom panel with a discoloured casing, a plain steel noticeboard frame carrying no "
    "legible content, and neglected shrubs against the wall.",
    "sober documentary architectural real-estate photography, 35mm lens, natural overcast light, "
    "realistic surface deterioration.",
    "wide 16:9 landscape from the road, gate and wall filling the frame, the building visible beyond. "
    + constraints(
        "clearly overdue for maintenance but plausible and occupied, with no disaster, no collapse, no "
        "rubbish piles and no graffiti;"
    ),
)

east_amenities = house(
    EAST,
    "communal-amenities photograph",
    "an under-maintained communal courtyard between apartment blocks, with a cracked concrete walkway "
    "crossing patchy grass.",
    "a dry thinning lawn with bare patches, overgrown leggy shrubbery, one weathered wooden bench with "
    "flaking paint, a leaning clothesline frame carrying no washing, moss-stained paving, and the same "
    "weathered facades behind.",
    "sober documentary architectural real-estate photography, 35mm lens, soft natural daylight.",
    "wide 16:9 landscape of the courtyard, facades closing the background. "
    + constraints("neglected through lack of routine care, not vandalised or hazardous;"),
)

east_infra = house(
    EAST,
    "common-area condition photograph",
    "an exterior service area beside the apartment block: a stair landing, a concrete walkway and the "
    "base of a facade.",
    "cracked non-structural plaster with a stain running down from a leaking downpipe, flaking paint on "
    "the stair rail, weeds pushing through cracked paving joints, a communal light fitting missing its "
    "diffuser, and a rusted meter box.",
    "sober documentary architectural real-estate photography, 35mm lens, flat overcast light, realistic "
    "texture and scale.",
    "wide 16:9 landscape along the walkway, facade and services in view. "
    + constraints("deterioration shown through surface condition and deferred maintenance only;"),
)

# --------------------------------------------------------------- Quarry View Flats
QUARRY = (
    "the same original, fictional high-density older South African walk-up complex as the hero image: "
    "compact three-storey concrete-and-plaster blocks with dull grey-beige plaster and external access "
    "corridors."
)

quarry_entrance = house(
    QUARRY,
    "estate-access photograph",
    "a basic utilitarian entrance between high precast concrete boundary panels, on a worn hard-packed "
    "apron with broken asphalt at the edge.",
    "dull faded paint over the precast panels, a heavy weathered steel sliding gate on a rusted track, "
    "a simple access-control box with a scratched casing and a discoloured keypad, a bent galvanised "
    "pedestrian gate, and coarse weeds along the wall base.",
    "restrained documentary architectural real-estate photography, 35mm lens, flat natural daylight.",
    "wide 16:9 landscape from the road, walling and gate dominating, walk-up blocks rising behind. "
    + constraints(
        "basic and visibly poorly maintained, without vandalism or security dramatics;"
    ),
)

quarry_amenities = house(
    QUARRY,
    "communal-amenities photograph",
    "an open shared yard between two walk-up blocks, mostly hard-packed earth with worn paving at the "
    "edges.",
    "sparse tufts of coarse grass, a pair of plain concrete clothesline poles, a scuffed metal bench, "
    "an old concrete table, uneven drainage staining along the block base, and facades with external "
    "access corridors above.",
    "restrained documentary architectural real-estate photography, 35mm lens, flat natural daylight, "
    "realistic material wear.",
    "wide 16:9 landscape of the yard with the blocks closing the view. "
    + constraints(
        "neglect conveyed through accumulated wear and absent upkeep, with no poverty stereotype and no "
        "unsafe depictions of residents;"
    ),
)

quarry_infra = house(
    QUARRY,
    "common-area condition photograph",
    "an external concrete walkway and open stairwell on the side of one walk-up block, above a cracked "
    "concrete stormwater channel.",
    "weathered external concrete stairs with scuffed nosings, a stained facade below the stair, a "
    "cracked and silted open drainage channel with weeds in it, a communal light fitting with exposed "
    "but intact shrouding, and ordinary wear across every common surface.",
    "restrained documentary architectural real-estate photography, 35mm lens, flat overcast light.",
    "wide 16:9 landscape taking in the stair, walkway, channel and facade together. "
    + constraints("obvious but realistic deferred maintenance with no structural failure;"),
)

remaining = [
    record("willowbrook-mews-02-entrance.jpg", willow_entrance),
    record("willowbrook-mews-03-amenities.jpg", willow_amenities),
    record("willowbrook-mews-04-infrastructure.jpg", willow_infra),
    record("lakeside-gardens-01-hero.jpg", already_sent["lakeside-gardens-01-hero.jpg"]),
    record("lakeside-gardens-02-entrance.jpg", lake_entrance),
    record("lakeside-gardens-03-amenities.jpg", lake_amenities),
    record("lakeside-gardens-04-infrastructure.jpg", lake_infra),
    record("eastbank-court-01-hero.jpg", already_sent["eastbank-court-01-hero.jpg"]),
    record("eastbank-court-02-entrance.jpg", east_entrance),
    record("eastbank-court-03-amenities.jpg", east_amenities),
    record("eastbank-court-04-infrastructure.jpg", east_infra),
    record("quarry-view-flats-01-hero.jpg", already_sent["quarry-view-flats-01-hero.jpg"]),
    record("quarry-view-flats-02-entrance.jpg", quarry_entrance),
    record("quarry-view-flats-03-amenities.jpg", quarry_amenities),
    record("quarry-view-flats-04-infrastructure.jpg", quarry_infra),
]

os.makedirs("tmp/imagegen", exist_ok=True)
out_path = "tmp/imagegen/estate-demo-images.prompts.jsonl"
with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
    for item in remaining:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")

# The three hero prompts are reused, so they must be byte-identical to the log.
reused = [
    name
    for name in (
        "lakeside-gardens-01-hero.jpg",
        "eastbank-court-01-hero.jpg",
        "quarry-view-flats-01-hero.jpg",
    )
    if any(r["out"] == name and r["prompt"] == already_sent[name] for r in remaining)
]
print(f"wrote {len(remaining)} records -> {out_path}")
print(f"reused verbatim from the existing log: {len(reused)} -> {', '.join(reused)}")
for index, item in enumerate(remaining, 1):
    print(f"  {index:2d}. {item['out']:44s} prompt {len(item['prompt']):4d} chars")
