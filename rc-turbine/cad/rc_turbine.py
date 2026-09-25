"""
RC micro-turbine (KJ-66-class layout), parametric CadQuery model.

Run:   python rc_turbine.py            -> writes STEP/STL files to ./out
       python rc_turbine.py --check    -> also runs the interference check

Units: millimetres. Engine axis = +Z. Front face of the intake at z ~ -6,
exhaust exit at z = NOZ_EXIT_Z. "Up" (top of engine, fittings side) = +Y.

Everything that sets the size of the engine is in PARAMS below. The z
"stations" further down are derived from PARAMS so the parts stay in step
when you change a value. Purchased parts (compressor wheel, turbine wheel,
bearings, glow plug, starter motor, fittings) are modelled as envelopes: MEASURE
THE PARTS YOU BUY and enter their real dimensions here before machining anything.
"""
import math
import os
import sys

import cadquery as cq
from cadquery import Vector as V

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
PARAMS = dict(
    # Purchased rotating parts (typical 66 mm hobby wheels)
    comp_tip_d=66.0,        # compressor wheel exducer diameter
    comp_inducer_d=45.0,    # compressor inducer tip diameter
    comp_exit_width=4.0,    # blade height at the exducer
    comp_len=21.0,          # inducer face to exducer hub face (axial)
    comp_back_t=2.5,        # compressor back-plate thickness
    wheel_bore=6.0,         # bore of both wheels (M6 shaft ends)
    turb_tip_d=66.0,        # turbine wheel tip diameter
    turb_hub_d=43.0,        # turbine blade root diameter
    turb_width=10.0,        # turbine blade axial width
    tip_clearance=0.3,      # radial clearance, compressor and turbine shrouds
    # Bearings: 608-size hybrid ceramic (8 x 22 x 7)
    brg_id=8.0, brg_od=22.0, brg_w=7.0,
    brg_span=94.0,          # distance between bearing inner faces
    # Casing
    casing_od=110.0, casing_wall=0.6,
    flange_od=120.0,
    # Combustor
    liner_od=95.0, liner_id_inner=36.0, liner_t=0.5,
    comb_len=70.0,          # front plate to start of the outer cone
    n_sticks=6, stick_d=6.0, stick_len=58.0,
    # Diffuser
    n_radial_vanes=12, n_axial_vanes=20, axial_diff_len=30.0,
    # NGV / nozzle
    n_ngv=19, n_turb_blades=25, ngv_len=10.0,
    nozzle_exit_d=54.0, nozzle_len=48.0,
    # Fasteners
    m3_clear=3.4, m3_tap=2.5, n_flange_screws=8, flange_pcd=115.0,
    # Mounting
    mount_plate_w=90.0, mount_plate_t=4.0, mount_hole_d=4.5, mount_drop=18.0,
)
p = PARAMS

# ---------------------------------------------------------------------------
# Derived radii and axial stations
# ---------------------------------------------------------------------------
R_CAS = p["casing_od"] / 2                 # 55
R_CASI = R_CAS - p["casing_wall"]          # 53.5
R_FL = p["flange_od"] / 2                  # 60
R_PCD = p["flange_pcd"] / 2                # 57.5
R_TIP = p["comp_tip_d"] / 2                # 33
R_IND = p["comp_inducer_d"] / 2            # 22.5
R_BORE = p["wheel_bore"] / 2               # 3
R_SH = p["brg_id"] / 2                     # 4
R_BRG = p["brg_od"] / 2                    # 11
CL = p["tip_clearance"]

Z_IND = 14.0                               # compressor inducer face
Z_CEX_F = Z_IND + p["comp_len"] - p["comp_exit_width"]   # exducer shroud edge (31)
Z_CEX_H = Z_IND + p["comp_len"]            # exducer hub edge (35)
Z_CBACK = Z_CEX_H + p["comp_back_t"]       # wheel back face (37.5)
Z_DIFF_R = Z_CBACK + 0.5                   # diffuser plate front (inner zone)
Z_DIFF_B = Z_DIFF_R + 5.0                  # diffuser plate rear face (43.5)
Z_AXD_END = Z_CEX_H + p["axial_diff_len"]  # end of axial diffuser (65)
Z_BRG1 = Z_DIFF_B                          # front bearing front face
Z_SHOULDER1 = Z_BRG1 + p["brg_w"]          # shaft shoulder 1
Z_SHOULDER2 = Z_SHOULDER1 + p["brg_span"]  # shaft shoulder 2
Z_BRG2_E = Z_SHOULDER2 + p["brg_w"]        # rear bearing rear face
Z_TUN_E = Z_BRG2_E                         # tunnel rear face
Z_COMB_F = Z_AXD_END + 12.0                # combustor front plate (77)
Z_OCONE = Z_COMB_F + p["comb_len"]         # outer liner cone start
Z_NGV_F = Z_TUN_E + 5.0                    # NGV hub flare
Z_NGV_V0 = Z_NGV_F + 4.0                   # NGV vane leading edge
Z_NGV_V1 = Z_NGV_V0 + p["ngv_len"]
Z_NGV_E = Z_NGV_V1 + 2.0                   # NGV rear / flange front
Z_TURB = Z_NGV_E + 3.0                     # turbine wheel front face
Z_TURB_E = Z_TURB + p["turb_width"] + 2.0  # turbine hub rear face
Z_NOZ_F = Z_NGV_E + 2.0                    # nozzle flange front
NOZ_EXIT_Z = Z_TURB_E + p["nozzle_len"]
R_LO = p["liner_od"] / 2
R_LI = p["liner_id_inner"] / 2
R_NGV_H = p["turb_hub_d"] / 2 + 0.2        # NGV hub radius at vanes
R_NGV_T = p["turb_tip_d"] / 2 + CL + 0.2   # NGV tip radius

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rev(pts):
    """Revolve a closed (r, z) profile about the Z axis."""
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def tube(ri, ro, z0, z1):
    return rev([(ri, z0), (ro, z0), (ro, z1), (ri, z1)])


def polar(r, a_deg, z=0.0):
    a = math.radians(a_deg)
    return V(r * math.cos(a), r * math.sin(a), z)


def radial_dir(a_deg):
    a = math.radians(a_deg)
    return V(math.cos(a), math.sin(a), 0)


def cyl(r, h, pnt, d):
    return cq.Solid.makeCylinder(r, h, pnt, d)


def union_all(shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out.clean()


def cut_all(base, cutters):
    if not cutters:
        return base
    return base.cut(cq.Compound.makeCompound(cutters)).clean()


def axial_holes(r_pcd, n, d, z0, h, phase=0.0):
    return [cyl(d / 2, h, polar(r_pcd, phase + i * 360 / n, z0), V(0, 0, 1)) for i in range(n)]


def radial_holes(r0, n, d, z, h, phase=0.0):
    return [cyl(d / 2, h, polar(r0, phase + i * 360 / n, z), radial_dir(phase + i * 360 / n)) for i in range(n)]


def meridional_plate(pts, t):
    """Flat plate lying in the XZ plane (pts are (r, z)), thickness t along Y."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(t / 2, both=True).val()


def tilted_plate(r0, r1, z_c, axial_len, t, tilt_deg):
    """Blade/vane: plate spanning r0..r1, rotated about its radial axis by tilt."""
    b = cq.Solid.makeBox(r1 - r0, t, axial_len, V(r0, -t / 2, -axial_len / 2))
    b = b.rotate(V(0, 0, 0), V(1, 0, 0), tilt_deg)
    return b.translate(V(0, 0, z_c))


def pattern(shape, n, phase=0.0):
    return [shape.rotate(V(0, 0, 0), V(0, 0, 1), phase + i * 360 / n) for i in range(n)]


def plane_for(pos, d):
    d = d.normalized()
    ref = V(0, 0, 1) if abs(d.z) < 0.9 else V(1, 0, 0)
    x = ref.cross(d).normalized()
    return cq.Plane(origin=pos, xDir=x, normal=d)


def cap_screw(d, length, pos, direction):
    """ISO 4762 socket head cap screw, simplified. Head sits at pos, shank along direction."""
    head_d, head_h, key = 1.6 * d + 0.7, d, 0.8 * d + 0.05
    pl = plane_for(pos, direction)
    shank = cq.Workplane(pl).circle(d / 2).extrude(length).val()
    back = plane_for(pos, direction * -1)
    head = cq.Workplane(back).circle(head_d / 2).extrude(head_h).val()
    sock = cq.Workplane(plane_for(pos + direction * -head_h, direction)).polygon(6, key * 1.1547).extrude(head_h * 0.6).val()
    return shank.fuse(head).cut(sock).clean()


def hex_nut(af, h, bore, z0):
    return cq.Workplane("XY").workplane(offset=z0).polygon(6, af * 1.1547).extrude(h).faces(">Z").workplane().hole(bore).val()


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
# Compressor shroud curve (wheel side) and hub curve, (r, z)
SHROUD = [(R_IND, Z_IND), (R_IND + 0.2, Z_IND + 4), (R_IND + 1.0, Z_IND + 8), (R_IND + 3.0, Z_IND + 12),
          (R_IND + 6.0, Z_IND + 15), (R_TIP, Z_CEX_F)]
HUB = [(R_BORE + 3.0, Z_IND), (R_BORE + 4.0, Z_IND + 6), (R_BORE + 8.0, Z_IND + 12), (R_BORE + 16.0, Z_IND + 17.5),
       (R_TIP, Z_CEX_H)]
RADIAL_VANE_SCREW_R = 46.0
N_DIFF_SCREWS = 4


def radial_vane_geom(i):
    """Wedge vane of the radial diffuser: returns (solid, screw point)."""
    n = p["n_radial_vanes"]
    a0 = i * 360 / n
    r0, r1 = R_TIP + 1.5, 49.5
    le = math.radians(a0)
    te0, te1 = math.radians(a0 + 7), math.radians(a0 + 15)
    pts = [(r0 * math.cos(le), r0 * math.sin(le)),
           (r1 * math.cos(te0), r1 * math.sin(te0)),
           (r1 * math.cos(te1), r1 * math.sin(te1))]
    z0, z1 = Z_CEX_F + 0.05, Z_CEX_H
    solid = cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0).val()
    # screw point on the vane centreline at RADIAL_VANE_SCREW_R
    f = (RADIAL_VANE_SCREW_R - r0) / (r1 - r0)
    ac = a0 + f * 11
    return solid, polar(RADIAL_VANE_SCREW_R, ac)


def screw_vanes():
    n = p["n_radial_vanes"]
    step = n // N_DIFF_SCREWS
    return [radial_vane_geom(i)[1] for i in range(0, n, step)]


def make_compressor_wheel():
    prof = [(R_BORE, Z_IND)] + HUB + [(R_TIP, Z_CBACK), (R_BORE, Z_CBACK)]
    body = rev(prof)
    main = meridional_plate(SHROUD + list(reversed([(r - 0.4, z) for r, z in HUB])), 0.9)
    mid = 3
    split = meridional_plate(SHROUD[mid:] + list(reversed([(r - 0.4, z) for r, z in HUB[mid - 1:]])), 0.8)
    blades = pattern(main, 7) + pattern(split, 7, 360 / 14)
    return union_all([body] + blades)


def make_intake():
    inner = [(29.0, -4.0), (25.5, 0.0), (23.8, 5.0), (23.0, 10.0)] + [(r + CL, z) for r, z in SHROUD]
    prof = inner + [(R_FL, Z_CEX_F), (R_FL, Z_CEX_F - 4), (43.0, Z_CEX_F - 4), (38.5, 24.0), (35.0, 18.0), (33.5, 10.0),
                    (32.5, 2.0), (31.8, -2.5), (30.3, -4.4)]
    body = rev(prof)
    cutters = axial_holes(R_PCD, p["n_flange_screws"], p["m3_clear"], Z_CEX_F - 6, 10, 22.5)
    cutters += [cyl(p["m3_clear"] / 2, 10, V(s.x, s.y, Z_CEX_F - 6), V(0, 0, 1)) for s in screw_vanes()]
    cutters += [cyl(p["m3_tap"] / 2, 6, polar(28.5, a, 10.5), radial_dir(a)) for a in (90, 210, 330)]  # starter bracket
    return cut_all(body, cutters)


def make_diffuser():
    prof = [(R_BRG, Z_DIFF_R), (R_TIP + 1.0, Z_DIFF_R), (R_TIP + 1.0, Z_CEX_H), (50.0, Z_CEX_H), (50.0, Z_AXD_END),
            (48.0, Z_AXD_END), (48.0, Z_DIFF_B), (R_BRG, Z_DIFF_B)]
    body = rev(prof)
    vanes = [radial_vane_geom(i)[0] for i in range(p["n_radial_vanes"])]
    zc = (Z_CEX_H + Z_AXD_END) / 2
    axv = union_all(pattern(tilted_plate(49.6, R_CASI + 1.0, zc, p["axial_diff_len"] - 2, 1.2, 22), p["n_axial_vanes"]))
    axv = axv.intersect(tube(49.0, R_CASI - 0.1, Z_CEX_H, Z_AXD_END))
    part = union_all([body, axv] + vanes)
    cutters = [cyl(p["m3_tap"] / 2, 12, V(s.x, s.y, Z_CEX_F - 1), V(0, 0, 1)) for s in screw_vanes()]
    cutters += axial_holes(16.5, 4, p["m3_tap"], Z_DIFF_R - 1, 8, 45)
    return cut_all(part, cutters)


def make_tunnel():
    fl1, fl2 = Z_BRG1 + 4, Z_TUN_E - 3
    outer = [(R_BRG, Z_BRG1), (19.5, Z_BRG1), (19.5, fl1), (13.0, fl1), (13.0, fl2), (19.5, fl2), (19.5, Z_TUN_E),
             (R_BRG, Z_TUN_E), (R_BRG, Z_SHOULDER2 - 1.0), (9.5, Z_SHOULDER2 - 1.0), (9.5, Z_SHOULDER1),
             (R_BRG, Z_SHOULDER1)]
    body = rev(outer)
    a_l, z_l = FITTINGS["lube"]
    boss = cyl(3.0, 4.0, polar(12.0, a_l, z_l), radial_dir(a_l))
    body = body.fuse(boss).clean()
    cutters = axial_holes(16.5, 4, p["m3_clear"], Z_BRG1 - 1, 7, 45)
    cutters += axial_holes(16.5, 4, p["m3_tap"], fl2 - 1, 5, 45)
    cutters += [cyl(0.9, 10, polar(8.0, a_l, z_l), radial_dir(a_l))]   # lube port
    return cut_all(body, cutters)


def make_shaft():
    z_front = Z_IND - 5.0
    return rev([(0, z_front), (R_BORE, z_front), (R_BORE, Z_CBACK), (R_SH, Z_CBACK), (R_SH, Z_SHOULDER1),
                (R_SH + 0.5, Z_SHOULDER1), (R_SH + 0.5, Z_SHOULDER2), (R_SH, Z_SHOULDER2), (R_SH, Z_TURB),
                (R_BORE, Z_TURB), (R_BORE, Z_TURB_E + 6.5), (0, Z_TURB_E + 6.5)])


def make_bearing(z0):
    t = p["brg_w"]
    inner = tube(R_SH, R_SH + 2.2, z0, z0 + t)
    outer = tube(R_BRG - 2.2, R_BRG, z0, z0 + t)
    rc = (R_SH + 2.2 + R_BRG - 2.2) / 2
    balls = [cq.Solid.makeSphere(2.0, polar(rc, i * 360 / 8, z0 + t / 2), angleDegrees1=-90, angleDegrees2=90) for i in range(8)]
    return union_all([inner, outer] + balls)


def make_sleeves():
    front = tube(R_SH, 6.0, Z_CBACK, Z_BRG1)
    rear = tube(R_SH, 6.0, Z_BRG2_E, Z_TURB)
    spring = tube(R_BRG - 2.5, R_BRG - 0.1, Z_SHOULDER2 - 1.0, Z_SHOULDER2 - 0.3)  # wave-spring envelope
    return front, rear, spring


def make_combustor():
    t = p["liner_t"]
    z0, z_ic = Z_COMB_F, Z_OCONE - 5
    outer = rev([(R_LO - t, z0), (R_LO, z0), (R_LO, Z_OCONE), (R_NGV_T + 1.7, Z_NGV_F), (R_NGV_T + 1.7, Z_NGV_F + 4),
                 (R_NGV_T + 1.2, Z_NGV_F + 4), (R_NGV_T + 1.2, Z_NGV_F), (R_LO - t, Z_OCONE)])
    r_seat = 21.3
    inner = rev([(R_LI, z0), (R_LI + t, z0), (R_LI + t, z_ic), (r_seat + t, Z_TUN_E), (r_seat + t, Z_NGV_F),
                 (r_seat, Z_NGV_F), (r_seat, Z_TUN_E), (R_LI, z_ic)])
    plate = tube(R_LI, R_LO, z0 - 1.0, z0)
    sticks = []
    for i in range(p["n_sticks"]):
        c = polar((R_LI + R_LO) / 2, i * 360 / p["n_sticks"], z0 - 3)
        s = cyl(p["stick_d"] / 2, p["stick_len"], c, V(0, 0, 1)).cut(cyl(p["stick_d"] / 2 - 0.3, p["stick_len"], c, V(0, 0, 1)))
        sticks.append(s)
    body = union_all([outer, inner, plate] + sticks)
    cut = []
    for i in range(p["n_sticks"]):
        c = polar((R_LI + R_LO) / 2, i * 360 / p["n_sticks"], z0 - 2)
        cut.append(cyl(p["stick_d"] / 2 - 0.3, 3, c, V(0, 0, 1)))
    # outer liner air holes: primary, secondary, dilution
    for z, n, d in ((z0 + 12, 18, 3.0), (z0 + 32, 12, 4.0), (z0 + 58, 10, 6.0)):
        cut += radial_holes(R_LO - 2, n, d, z, 4, 180 / n)
    cut += radial_holes(R_LI - 2, 12, 2.5, z0 + 18, 4)
    cut += radial_holes(R_LI - 2, 8, 4.0, z0 + 45, 4, 22.5)
    cut.append(cyl(2.5, 4, polar(R_LO - 2, 200, z0 + 15), radial_dir(200)))   # glow plug port
    return cut_all(body, cut)


def make_ngv():
    hub = rev([(7.0, Z_TUN_E), (21.25, Z_TUN_E), (21.25, Z_NGV_F), (R_NGV_H, Z_NGV_F + 2), (R_NGV_H, Z_NGV_E),
               (R_NGV_H - 1.5, Z_NGV_E), (R_NGV_H - 1.5, Z_NGV_F + 2), (19.8, Z_TUN_E + 3), (7.0, Z_TUN_E + 3)])
    ring = rev([(R_NGV_T, Z_NGV_F), (R_NGV_T + 1.2, Z_NGV_F), (R_NGV_T + 1.2, Z_NGV_E), (R_FL, Z_NGV_E),
                (R_FL, Z_NGV_E + 1.5), (R_NGV_T, Z_NGV_E + 1.5)])
    zc = (Z_NGV_V0 + Z_NGV_V1) / 2
    vanes = union_all(pattern(tilted_plate(R_NGV_H - 1.0, R_NGV_T + 1.0, zc, p["ngv_len"] + 3, 1.2, -58), p["n_ngv"]))
    vanes = vanes.intersect(tube(R_NGV_H - 0.3, R_NGV_T + 0.3, Z_NGV_V0 - 1, Z_NGV_V1 + 1))
    part = union_all([hub, ring, vanes])
    cut = axial_holes(16.5, 4, p["m3_clear"], Z_TUN_E - 1, 6, 45)
    cut += axial_holes(R_PCD, p["n_flange_screws"], p["m3_clear"], Z_NGV_E - 1, 5, 22.5)
    return cut_all(part, cut)


def make_turbine_wheel():
    rh = p["turb_hub_d"] / 2
    disk = rev([(R_BORE, Z_TURB), (rh, Z_TURB + 0.5), (rh, Z_TURB + p["turb_width"] + 1.5), (10.0, Z_TURB_E),
                (R_BORE, Z_TURB_E)])
    zc = Z_TURB + 1 + p["turb_width"] / 2
    blades = union_all(pattern(tilted_plate(rh - 0.5, p["turb_tip_d"] / 2 + 1, zc, p["turb_width"], 1.3, 38), p["n_turb_blades"]))
    blades = blades.intersect(tube(rh - 0.6, p["turb_tip_d"] / 2, Z_TURB, Z_TURB + p["turb_width"] + 2))
    return union_all([disk, blades])


def make_casing():
    tube_ = tube(R_CASI, R_CAS, Z_CEX_F, Z_NGV_E)
    ff = tube(R_CAS - 0.01, R_FL, Z_CEX_F, Z_CEX_F + 3)
    rf = tube(R_CAS - 0.01, R_FL, Z_NGV_E - 3, Z_NGV_E)
    bosses = [cyl(4.5, 3.0, polar(R_CAS - 0.5, 200, Z_COMB_F + 15), radial_dir(200))]  # glow plug boss
    body = union_all([tube_, ff, rf] + bosses)
    cut = axial_holes(R_PCD, p["n_flange_screws"], p["m3_tap"], Z_CEX_F - 1, 5, 22.5)
    cut += axial_holes(R_PCD, p["n_flange_screws"], p["m3_tap"], Z_NGV_E - 4, 5, 22.5)
    for a, z in FITTINGS.values():
        cut.append(cyl(2.1, 6, polar(R_CASI - 1, a, z), radial_dir(a)))
    cut.append(cyl(2.5, 8, polar(R_CASI - 1, 200, Z_COMB_F + 15), radial_dir(200)))
    return cut_all(body, cut)


def make_nozzle():
    t = 0.8
    r_sh = p["turb_tip_d"] / 2 + CL
    r_exit = p["nozzle_exit_d"] / 2
    z_fl0, z_fl1 = Z_NOZ_F, Z_NOZ_F + 2
    prof = [(r_sh, z_fl0), (R_FL, z_fl0), (R_FL, z_fl1), (r_sh + t, z_fl1), (r_sh + t, Z_TURB_E + 1),
            (r_sh + 1.0 + t, Z_TURB_E + 5), (r_exit + t, NOZ_EXIT_Z), (r_exit, NOZ_EXIT_Z), (r_sh + 1.0, Z_TURB_E + 5),
            (r_sh, Z_TURB_E + 1)]
    shell = rev(prof)
    zt = Z_TURB_E
    cone = rev([(0, zt + 30), (4.0, zt + 30), (20.5, zt + 2), (9.0, zt + 2), (9.0, zt + 2.8), (19.3, zt + 2.8),
                (3.4, zt + 29.2), (0, zt + 29.2)])   # 0.8 mm sheet tail cone, open over the turbine nut
    struts = pattern(meridional_plate([(12.0, Z_TURB_E + 8), (r_sh + 1.2, Z_TURB_E + 8), (r_sh + 1.2, Z_TURB_E + 16),
                                        (12.0, Z_TURB_E + 16)], 1.2), 3, 90)
    boss = cyl(3.5, 6, polar(r_sh + 0.5, 90, Z_TURB_E + 21), radial_dir(90))
    part = union_all([shell, cone, boss] + struts)
    cut = axial_holes(R_PCD, p["n_flange_screws"], p["m3_clear"], z_fl0 - 1, 5, 22.5)
    cut += axial_holes(46.0, p["n_flange_screws"], 10.0, z_fl0 - 1, 5, 0.0)   # lightening holes
    cut.append(cyl(0.85, 14, polar(r_sh - 4, 90, Z_TURB_E + 21), radial_dir(90)))
    return cut_all(part, cut)


# Fittings on the casing: name -> (angle deg, z)
FITTINGS = {"fuel": (90.0, Z_COMB_F - 8), "gas": (70.0, Z_COMB_F - 5), "lube": (110.0, Z_COMB_F - 2.5)}


def make_fitting(name):
    a, z = FITTINGS[name]
    d = radial_dir(a)
    base = polar(R_CAS, a, z)
    hexb = cq.Workplane(plane_for(base, d)).polygon(6, 7 * 1.1547).extrude(4).val()
    barb = cyl(2.0, 9, base + d * 4, d)
    stub = cyl(2.0, p["casing_wall"] + 1.5, base - d * (p["casing_wall"] + 1.5), d)
    nut = cq.Workplane(plane_for(base - d * (p["casing_wall"] + 2.5), d)).polygon(6, 7 * 1.1547).extrude(1.0).val()
    return union_all([hexb, barb, stub, nut]).cut(cyl(1.0, 20, base - d * 5, d)).clean()


def make_fuel_system():
    """Fuel manifold + needles, gas start ring, lube line (all 3 mm / 2.5 mm tube)."""
    z_fuel = FITTINGS["fuel"][1]
    z_gas = FITTINGS["gas"][1]
    r_st = (R_LI + R_LO) / 2
    fuel_ring = cq.Solid.makeTorus(r_st, 1.5, pnt=V(0, 0, z_fuel), dir=V(0, 0, 1))
    needles = [cyl(0.5, (Z_COMB_F + 2) - z_fuel - 1.0, polar(r_st, i * 360 / p["n_sticks"], z_fuel + 1.0), V(0, 0, 1))
               for i in range(p["n_sticks"])]
    a = FITTINGS["fuel"][0]
    fuel_feed = cyl(1.5, R_CASI - 3.0 - (r_st + 1.2), polar(r_st + 1.2, a, z_fuel), radial_dir(a))
    fuel = fuel_ring.fuse(fuel_feed, *needles)
    r_g = 42.0
    gas_ring = cq.Solid.makeTorus(r_g, 1.2, pnt=V(0, 0, z_gas), dir=V(0, 0, 1))
    a = FITTINGS["gas"][0]
    gas = gas_ring.fuse(cyl(1.2, R_CASI - 3.0 - (r_g + 1.0), polar(r_g + 1.0, a, z_gas), radial_dir(a))).clean()
    a, z = FITTINGS["lube"]
    lube = cyl(1.25, R_CASI - 3.0 - 16.0, polar(16.0, a, z), radial_dir(a))
    return fuel, gas, lube


def make_glow_plug():
    a, z = 200.0, Z_COMB_F + 15
    d = radial_dir(a)
    base = polar(R_CAS + 3.0, a, z)
    hexb = cq.Workplane(plane_for(base, d)).polygon(6, 10 * 1.1547).extrude(6).val()
    thread = cyl(2.4, 3.0 + 3.0, base - d * 6.0, d)
    element = cyl(1.4, 8.0, base - d * 14.0, d)
    term = cyl(1.5, 5, base + d * 6, d)
    return union_all([hexb, thread, element, term])


def make_thermocouple():
    a, z = 90.0, Z_TURB_E + 21
    d = radial_dir(a)
    r_sh = p["turb_tip_d"] / 2 + CL
    probe = cyl(0.75, 18, polar(r_sh - 12, a, z), d)
    fit = cq.Workplane(plane_for(polar(r_sh + 6.5, a, z), d)).polygon(6, 8 * 1.1547).extrude(5).val()
    lead = cyl(1.0, 20, polar(r_sh + 11.5, a, z), d)
    return union_all([probe, fit, lead])


def make_comp_nut():
    body = hex_nut(10.0, 6.0, p["wheel_bore"], Z_IND - 6.0)
    cone = cq.Solid.makeCone(5.5, 3.0, 4.0, V(0, 0, Z_IND - 6.0), V(0, 0, -1))
    return body.fuse(cone).clean()


def make_turb_nut():
    return hex_nut(10.0, 5.0, p["wheel_bore"], Z_TURB_E)


# Starter: motor + rubber clutch cone + 3-arm bracket screwed to the intake
Z_STARTER = -34.0


def make_starter_bracket():
    hub = tube(14.2, 17.5, Z_STARTER - 10, Z_STARTER)
    arms = []
    for a in (90, 210, 330):
        arm = meridional_plate([(15.0, Z_STARTER - 10), (18.5, Z_STARTER - 10), (18.5, Z_STARTER), (38.5, -9.0),
                                (38.5, 13.0), (34.3, 13.0), (34.3, -8.0), (15.0, Z_STARTER - 4)], 8.0)
        arms.append(arm.rotate(V(0, 0, 0), V(0, 0, 1), a))
    body = union_all([hub] + arms)
    cut = [cyl(p["m3_clear"] / 2, 8, polar(33.0, a, 10.5), radial_dir(a)) for a in (90, 210, 330)]
    return cut_all(body, cut)


def make_starter_motor():
    can = cyl(14.0, 30, V(0, 0, Z_STARTER - 30 + 0), V(0, 0, 1)).translate(V(0, 0, 0))
    shaft = cyl(1.5, 8, V(0, 0, Z_STARTER), V(0, 0, 1))
    return can.fuse(shaft).clean()


def make_starter_cone():
    z0 = Z_STARTER + 6
    body = cyl(6.0, (Z_IND - 6.0 - 4.0) - z0 - 1.2, V(0, 0, z0), V(0, 0, 1))
    tip = cq.Solid.makeCone(6.0, 4.0, 2.2, V(0, 0, Z_IND - 6.0 - 4.0 - 1.2 - 2.2), V(0, 0, 1))
    return body.fuse(tip).cut(cyl(1.5, 3.0, V(0, 0, z0), V(0, 0, 1))).clean()


# Mounting: two split clamp bands + base plate
MOUNT_Z = (Z_COMB_F + 28, Z_NGV_E - 16)
Y_PLATE = -(R_CAS + p["mount_drop"])


def make_mount_band(zc):
    w = 12.0
    band = tube(R_CAS, R_CAS + 3, zc - w / 2, zc + w / 2)
    gap = cq.Solid.makeBox(6, 10, w + 2, V(-3, R_CAS - 2, zc - w / 2 - 1))
    ears = [cq.Solid.makeBox(5, 8, w, V(s, R_CAS + 1.0, zc - w / 2)) for s in (-8.0, 3.0)]
    foot = cq.Solid.makeBox(24, p["mount_drop"] - 1.5, w, V(-12, Y_PLATE, zc - w / 2))
    body = union_all([band] + ears + [foot]).cut(gap).clean()
    body = body.cut(cyl(R_CAS, w + 2, V(0, 0, zc - w / 2 - 1), V(0, 0, 1))).clean()
    cut = [cyl(p["m3_clear"] / 2, 20, V(-10, R_CAS + 5.0, zc), V(1, 0, 0)),
           cyl(p["m3_tap"] / 2, 10, V(0, Y_PLATE - 1, zc), V(0, 1, 0))]
    return cut_all(body, cut)


def make_mount_plate():
    z0, z1 = MOUNT_Z[0] - 20, MOUNT_Z[1] + 20
    wpl = p["mount_plate_w"]
    plate = cq.Solid.makeBox(wpl, p["mount_plate_t"], z1 - z0, V(-wpl / 2, Y_PLATE - p["mount_plate_t"], z0))
    cut = [cyl(p["mount_hole_d"] / 2, 20, V(x, Y_PLATE - 10, z), V(0, 1, 0))
           for x in (-wpl / 2 + 8, wpl / 2 - 8) for z in (z0 + 8, z1 - 8)]
    cut += [cyl(p["m3_clear"] / 2, 20, V(0, Y_PLATE - 10, z), V(0, 1, 0)) for z in MOUNT_Z]
    return cut_all(plate, cut)


def fasteners():
    """All screws with their positions: list of (name, solid)."""
    out = []
    # intake -> casing front flange: M3x8
    for i in range(p["n_flange_screws"]):
        pos = polar(R_PCD, 22.5 + i * 360 / p["n_flange_screws"], Z_CEX_F - 4)
        out.append(("M3x8 intake-casing", cap_screw(3, 8, pos, V(0, 0, 1))))
    # intake -> diffuser vanes: M3x10
    for s in screw_vanes():
        out.append(("M3x10 intake-diffuser", cap_screw(3, 10, V(s.x, s.y, Z_CEX_F - 4), V(0, 0, 1))))
    # tunnel -> diffuser: M3x8 from the rear of the tunnel flange
    for i in range(4):
        pos = polar(16.5, 45 + i * 90, Z_BRG1 + 4)
        out.append(("M3x8 tunnel-diffuser", cap_screw(3, 8, pos, V(0, 0, -1))))
    # NGV hub -> tunnel: M3x6
    for i in range(4):
        pos = polar(16.5, 45 + i * 90, Z_TUN_E + 3)
        out.append(("M3x6 NGV-tunnel", cap_screw(3, 6, pos, V(0, 0, -1))))
    # nozzle + NGV flange -> casing rear flange: M3x8
    for i in range(p["n_flange_screws"]):
        pos = polar(R_PCD, 22.5 + i * 360 / p["n_flange_screws"], Z_NOZ_F + 3)
        out.append(("M3x8 nozzle-casing", cap_screw(3, 8, pos, V(0, 0, -1))))
    # starter bracket -> intake: M3x6 radial
    for a in (90, 210, 330):
        out.append(("M3x8 starter bracket", cap_screw(3, 8, polar(38.5, a, 10.5), radial_dir(a) * -1)))
    # mount clamp screws (M3x16 across the ears) and band-to-plate screws (M3x10 from below)
    for zc in MOUNT_Z:
        out.append(("M3x16 mount clamp", cap_screw(3, 16, V(-8.0, R_CAS + 5.0, zc), V(1, 0, 0))))
        out.append(("M3x10 mount-plate", cap_screw(3, 10, V(0, Y_PLATE - p["mount_plate_t"], zc), V(0, 1, 0))))
    return out


# ---------------------------------------------------------------------------
# Build + export
# ---------------------------------------------------------------------------
AL = cq.Color(0.72, 0.75, 0.78)
SS = cq.Color(0.55, 0.56, 0.58)
INC = cq.Color(0.47, 0.40, 0.33)
STEEL = cq.Color(0.35, 0.37, 0.40)
BRASS = cq.Color(0.80, 0.65, 0.30)
DARK = cq.Color(0.15, 0.16, 0.17)
TI = cq.Color(0.62, 0.66, 0.70)

DENSITY = {"al": 2.70e-3, "ss": 7.9e-3, "inc": 8.0e-3, "steel": 7.85e-3, "brass": 8.5e-3, "other": 2.0e-3}  # g/mm^3


def build():
    parts = []  # (name, solid, color, material, kind)

    def add(name, solid, color, material, kind):
        parts.append((name, solid, color, material, kind))

    add("01_intake_cover", make_intake(), AL, "al", "make")
    add("02_compressor_wheel_ENVELOPE", make_compressor_wheel(), TI, "al", "buy")
    add("03_diffuser", make_diffuser(), AL, "al", "make")
    add("04_bearing_tunnel", make_tunnel(), AL, "al", "make")
    add("05_shaft", make_shaft(), STEEL, "steel", "make")
    add("06_bearing_front_608", make_bearing(Z_BRG1), STEEL, "steel", "buy")
    add("06_bearing_rear_608", make_bearing(Z_SHOULDER2), STEEL, "steel", "buy")
    f, r, s = make_sleeves()
    add("07_front_sleeve", f, STEEL, "steel", "make")
    add("07_rear_sleeve", r, STEEL, "steel", "make")
    add("07_rear_bearing_wave_spring", s, STEEL, "steel", "buy")
    add("08_combustor", make_combustor(), SS, "ss", "make")
    add("09_ngv", make_ngv(), INC, "inc", "make")
    add("10_turbine_wheel_ENVELOPE", make_turbine_wheel(), INC, "inc", "buy")
    add("11_casing", make_casing(), SS, "ss", "make")
    add("12_nozzle", make_nozzle(), SS, "ss", "make")
    add("13_compressor_nut", make_comp_nut(), STEEL, "steel", "make")
    add("13_turbine_nut", make_turb_nut(), STEEL, "steel", "buy")
    fuel, gas, lube = make_fuel_system()
    add("14_fuel_manifold", fuel, BRASS, "ss", "make")
    add("14_gas_ring", gas, BRASS, "ss", "make")
    add("14_lube_line", lube, BRASS, "ss", "make")
    for k in FITTINGS:
        add(f"15_fitting_{k}", make_fitting(k), BRASS, "brass", "buy")
    add("16_glow_plug", make_glow_plug(), STEEL, "steel", "buy")
    add("17_thermocouple_K", make_thermocouple(), STEEL, "steel", "buy")
    add("18_starter_bracket", make_starter_bracket(), AL, "al", "make")
    add("18_starter_motor_ENVELOPE", make_starter_motor(), DARK, "other", "buy")
    add("18_starter_cone", make_starter_cone(), DARK, "other", "make")
    for i, zc in enumerate(MOUNT_Z):
        add(f"19_mount_band_{i + 1}", make_mount_band(zc), AL, "al", "make")
    add("20_mount_plate", make_mount_plate(), AL, "al", "make")
    for i, (nm, sol) in enumerate(fasteners()):
        add(f"99_screw_{i:02d}_{nm.replace(' ', '_')}", sol, DARK, "steel", "buy")
    return parts


def export(parts, out_dir):
    os.makedirs(os.path.join(out_dir, "parts"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "stl"), exist_ok=True)
    assy = cq.Assembly(name="rc_turbine")
    screws = cq.Assembly(name="fasteners")
    for name, solid, color, _, _ in parts:
        if name.startswith("99_"):
            screws.add(solid, name=name, color=color)
        else:
            assy.add(solid, name=name, color=color)
            cq.exporters.export(cq.Workplane().add(solid), os.path.join(out_dir, "parts", name + ".step"))
        cq.exporters.export(cq.Workplane().add(solid), os.path.join(out_dir, "stl", name + ".stl"),
                            tolerance=0.05, angularTolerance=0.2)
    assy.add(screws, name="fasteners")
    assy.export(os.path.join(out_dir, "rc_turbine_assembly.step"))


def report(parts, out_dir):
    rows, total = [], 0.0
    for name, solid, _, mat, kind in parts:
        m = solid.Volume() * DENSITY[mat]
        total += m
        rows.append((name, kind, mat, m))
    with open(os.path.join(out_dir, "mass_report.csv"), "w") as f:
        f.write("part,make_or_buy,material,mass_g\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]:.1f}\n")
        f.write(f"TOTAL,,,{total:.1f}\n")
    print(f"Estimated dry mass: {total:.0f} g")
    return rows


def interference_check(parts):
    """Report volume overlap between major parts (screws/fittings excluded)."""
    major = [(n, s) for n, s, *_ in parts if not n.startswith(("99_", "15_"))]
    boxes = [(n, s, s.BoundingBox()) for n, s in major]
    hits = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, s1, b1 = boxes[i]
            n2, s2, b2 = boxes[j]
            if b1.xmax < b2.xmin or b2.xmax < b1.xmin or b1.ymax < b2.ymin or b2.ymax < b1.ymin or \
               b1.zmax < b2.zmin or b2.zmax < b1.zmin:
                continue
            v = s1.intersect(s2).Volume()
            if v > 1.0:
                hits.append((n1, n2, v))
    return hits


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "out")
    parts = build()
    export(parts, out)
    report(parts, out)
    if "--check" in sys.argv:
        hits = interference_check(parts)
        print("Interference (mm^3):" if hits else "No interference above 1 mm^3 between major parts.")
        for h in hits:
            print(f"  {h[0]}  x  {h[1]}: {h[2]:.1f}")
