"""Canyon floor: rain-soaked roadway with embedded light rails, granite walks
and a plaza that leads up to the Spire."""

from . import materials as M
from .util import MeshBuilder, collection

CANYON_HALF = 18.0
ROAD_HALF = 11.5
Y0, Y1 = -400.0, 560.0


def build():
    col = collection('Street')
    asphalt = M.wet_asphalt()
    paving = M.wet_paving('Walks', tile=0.9, tone=0.08)
    rail_c = M.emission('LaneRailCyan', (0.1, 0.75, 1.0), 9.0)
    rail_a = M.emission('LaneRailAmber', (1.0, 0.5, 0.12), 4.0)
    curb = M.concrete('Curb', tone=0.12, panel=(2.0, 0.3), streaks=0.1)
    mats = [asphalt, paving, rail_c, rail_a, curb]
    mb = MeshBuilder()
    # wide asphalt field (extends under everything) and the walks
    mb.add([(-3000, -3000, 0), (3000, -3000, 0), (3000, 3000, 0), (-3000, 3000, 0)], [(0, 1, 2, 3)], 0)
    for s in (-1, 1):
        x0, x1 = sorted((s * ROAD_HALF, s * (CANYON_HALF + 40)))
        mb.box((x0, Y0, 0.0), (x1, Y1, 0.16), 1, faces=(1, 1, 0, 0, 0, 1))
        cx = s * ROAD_HALF
        mb.box((cx - 0.15, Y0, 0.0), (cx + 0.15, Y1, 0.17), 4)
        # amber guide line in the curb face
        mb.box((cx - s * 0.16 - 0.02, Y0, 0.07), (cx - s * 0.16 + 0.02, Y1, 0.1), 3)
    # cyan light rails: dashed lane markers set into the road
    y = Y0
    while y < Y1:
        for x in (-3.9, 3.9):
            mb.box((x - 0.07, y, -0.01), (x + 0.07, y + 5.0, 0.012), 2)
        y += 9.0
    # solid centre pair
    for x in (-0.18, 0.18):
        mb.box((x - 0.05, Y0, -0.01), (x + 0.05, Y1, 0.012), 3)
    return mb.to_object('CanyonFloor', mats, col)
