# Neo-Kowloon Sector 7 — The Canyon

A cyberpunk city district designed as architecture, not as a field of boxes:
a handful of signature buildings around one rain-soaked street canyon,
modelled procedurally in Python and path-traced in **Blender Cycles**
(physically based light transport: neon actually lights the concrete,
reflections are real, the haze scatters every lamp).

Everything is generated from code in [`blender/`](blender/): geometry,
materials, signage artwork, holograms, atmosphere, cameras.

![Canyon hero](screenshots/01_canyon_hero.jpg)

## The buildings

| | Design |
|---|---|
| **The Hive** | A terraced capsule megastructure. Four freestanding concrete pylons (service cores with glass lift shafts and colour-coded light slots) carry six receding terraces. Each terrace band is a frame into which ~4,400 prefabricated capsule homes are plugged — Nakagin-style porthole units, louvred studios and balcony units — each with its own interior light, porch downlight, drip edge and vent. Terrace slabs are drawn with continuous light lines and wash the capsules with grazing light. At street level a colonnaded arcade holds real shop interiors (ramen counters with lanterns, a cyber clinic, a neon bar, convenience stores with stocked shelves, roller-shuttered units) with their names in 3D lettering. |
| **The Spire** | The Kagemori arcology, 1 km tall, closing the end of the canyon. A chamfered-octagon golden glass core tapers from 84 m to 34 m, wrapped by a staggered bronze diagrid whose nodes carry amber lamps. Two sky lobbies are carved out of the core with gardens glowing behind the frame. Four blades lean together around a beacon, ringed by floating halos; a needle carries the aircraft lights. A monumental portal opens onto a plaza with a black reflecting pool; searchlights rake the haze. |
| **The Helix** | 76 superelliptic floor plates, each rotated 1.2° from the one below — a quarter turn over 300 m. Every slab edge carries an LED line drifting from cyan to violet with height, so the twist reads as spiralling bands of light. Fins follow the rotation; a lantern crown and needle cap it; it lands in a clear-glazed lobby drum around a warm timber core. |
| **The Monolith** | A 250 m board-formed concrete slab whose canyon face is a deep egg-crate of fins and floor ledges with rooms glowing at the back of every cell. Two colossal LED media walls hang proud of the grid in heavy bezels. It stands on giant pilotis over a glazed lobby and is capped by a crown cantilevering over the street, lit from beneath, with a rooftop sky-lounge, helipad and lattice masts. |
| **Bridges** | A sculpted maglev viaduct on Y-piers with a streamlined train crossing the canyon, and a ribbed glass sky-tube linking a Hive pylon to the Monolith. |
| **Holograms** | Two giant koi swimming through the canyon air: lofted bodies on an S-curved spine with twin-lobed tails, fins and barbels, rendered as pure light (kohaku patches, projected wire grid, scanlines, rim glow). |

Around them: a dense mid-rise city fabric and a distant skyline that the
haze turns into layered silhouettes, a low-lying mist layer, rain streaks
that catch the neon, wet asphalt with puddles and embedded light rails.

## Screenshots (3840 × 2160)

See [`screenshots/`](screenshots/).

## Rendering it yourself

Requires Python 3.13 and the `bpy` wheel (Blender as a module) plus Pillow:

```bash
python3 -m venv .venv && .venv/bin/pip install bpy pillow numpy
# quick previews
.venv/bin/python blender/build.py --shots all --res 960x540 --samples 16 --out renders/preview
# final 4K stills
.venv/bin/python blender/build.py --shots all --res 3840x2160 --samples 40 --final --out renders/4k
# or save the scene to open in Blender
.venv/bin/python blender/build.py --shots '' --save neo_kowloon.blend
```

Shots are defined in [`blender/cityparts/shots.py`](blender/cityparts/shots.py).

## Layout

```
blender/build.py                 entry point (build scene, render shots, save .blend)
blender/cityparts/
  hive.py  shops.py              capsule megastructure + arcade shop interiors
  spire.py                       the arcology
  helix.py                       twisting tower
  monolith.py                    brutalist media slab
  bridges.py                     maglev viaduct, train, sky tube
  holo.py                        holographic koi
  signs.py                       3D neon lettering, blade signs, poster artwork
  street.py fabric.py skyline.py canyon floor, city fabric, background towers
  materials.py                   Cycles node materials (concrete, curtain walls,
                                 capsules, wet asphalt, LED screens, holograms)
  scene.py shots.py util.py      render/atmosphere setup, cameras, mesh helpers
assets/fonts/                    OFL fonts (Google Fonts)
assets/generated/                generated poster artwork for the media walls
```

All brand names in the scene (Kagemori, Yurei, Mirai, Zenith) are invented.
