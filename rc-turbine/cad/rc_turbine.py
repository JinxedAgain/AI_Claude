"""
RC micro-turbine (KJ-66-class layout): CadQuery builder -> STEP / STL.

Run:   python rc_turbine.py            -> writes STEP/STL files to ./out
       python rc_turbine.py --check    -> also checks solid validity and interference

All dimensions come from ../fusion/RCTurbine/turbine_geometry.py, the same
module the Fusion script uses, so the two builds always match. Edit PARAMS
there. Purchased parts (compressor wheel, turbine wheel, bearings, glow plug,
starter motor, fittings) are envelopes: MEASURE THE PARTS YOU BUY and enter
their real dimensions before machining anything.
"""
import math
import os
import sys

import cadquery as cq
from cadquery import Vector as V

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fusion", "RCTurbine"))
import turbine_geometry as G  # noqa: E402

p = G.PARAMS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def rev(pts):
    """Revolve a closed (r, z) profile about the Z axis."""
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def vec(t):
    return V(*t)


def polar(r, a, z=0.0):
    return vec(G.polar(r, a, z))


def radial_dir(a):
    return vec(G.radial_dir(a))


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
    shank = cq.Workplane(plane_for(pos, direction)).circle(d / 2).extrude(length).val()
    head = cq.Workplane(plane_for(pos, direction * -1)).circle(head_d / 2).extrude(head_h).val()
    sock = cq.Workplane(plane_for(pos + direction * -head_h, direction)).polygon(6, key * 1.1547).extrude(head_h * 0.6).val()
    return shank.fuse(head).cut(sock).clean()


def hex_nut(af, h, bore, z0):
    return cq.Workplane("XY").workplane(offset=z0).polygon(6, af * 1.1547).extrude(h).faces(">Z").workplane().hole(bore).val()


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
def make_compressor_wheel():
    n = p["n_comp_blades"]
    blades = pattern(meridional_plate(G.comp_blade_main(), 0.9), n)
    blades += pattern(meridional_plate(G.comp_blade_splitter(), 0.8), n, 180 / n)
    return union_all([rev(G.comp_wheel_profile())] + blades)


def make_intake():
    body = rev(G.intake_profile())
    cutters = axial_holes(G.R_PCD, p["n_flange_screws"], p["m3_clear"], G.Z_CEX_F - 6, 10, 22.5)
    cutters += [cyl(p["m3_clear"] / 2, 10, V(x, y, G.Z_CEX_F - 6), V(0, 0, 1)) for x, y in G.screw_vanes()]
    cutters += [cyl(p["m3_tap"] / 2, 6, polar(28.5, a, G.STARTER_SCREW_Z), radial_dir(a)) for a in G.STARTER_ANGLES]
    return cut_all(body, cutters)


def make_diffuser():
    body = rev(G.diffuser_profile())
    vanes = []
    for i in range(p["n_radial_vanes"]):
        tri, z0, z1, _ = G.radial_vane(i)
        vanes.append(cq.Workplane("XY").workplane(offset=z0).polyline(tri).close().extrude(z1 - z0).val())
    zc = (G.Z_CEX_H + G.Z_AXD_END) / 2
    axv = union_all(pattern(tilted_plate(49.6, G.R_CASI + 1.0, zc, p["axial_diff_len"] - 2, 1.2, 22), p["n_axial_vanes"]))
    axv = axv.intersect(rev(G.rect(49.0, G.R_CASI - 0.1, G.Z_CEX_H, G.Z_AXD_END)))
    part = union_all([body, axv] + vanes)
    cutters = [cyl(p["m3_tap"] / 2, 12, V(x, y, G.Z_CEX_F - 1), V(0, 0, 1)) for x, y in G.screw_vanes()]
    cutters += axial_holes(G.TUNNEL_BOLT_R, 4, p["m3_tap"], G.Z_DIFF_R - 1, 8, 45)
    return cut_all(part, cutters)


def make_tunnel():
    a_l, z_l = G.FITTINGS["lube"]
    body = rev(G.tunnel_profile()).fuse(cyl(3.0, 4.0, polar(12.0, a_l, z_l), radial_dir(a_l))).clean()
    fz0, fz1 = G.TUNNEL_FRONT_FLANGE
    rz0, rz1 = G.TUNNEL_REAR_FLANGE
    cutters = axial_holes(G.TUNNEL_BOLT_R, 4, p["m3_clear"], fz0 - 1, fz1 - fz0 + 3, 45)
    cutters += axial_holes(G.TUNNEL_BOLT_R, 4, p["m3_tap"], rz0 - 1, rz1 - rz0 + 2, 45)
    cutters += [cyl(0.9, 10, polar(8.0, a_l, z_l), radial_dir(a_l))]   # lube port
    return cut_all(body, cutters)


def make_bearing(z0):
    t = p["brg_w"]
    inner = rev(G.rect(G.R_SH, G.R_SH + 2.2, z0, z0 + t))
    outer = rev(G.rect(G.R_BRG - 2.2, G.R_BRG, z0, z0 + t))
    rc = (G.R_SH + G.R_BRG) / 2
    balls = [cq.Solid.makeSphere(2.0, polar(rc, i * 45, z0 + t / 2), angleDegrees1=-90, angleDegrees2=90) for i in range(8)]
    return union_all([inner, outer] + balls)


def make_combustor():
    body = [rev(G.combustor_outer_profile()), rev(G.combustor_inner_profile()), rev(G.COMB_PLATE)]
    ri = p["stick_d"] / 2 - 0.3
    for i in range(p["n_sticks"]):
        c = polar(G.R_STICK, i * 360 / p["n_sticks"], G.STICK_Z0)
        body.append(cyl(p["stick_d"] / 2, p["stick_len"], c, V(0, 0, 1)).cut(cyl(ri, p["stick_len"], c, V(0, 0, 1))))
    part = union_all(body)
    cut = [cyl(ri, 3, polar(G.R_STICK, i * 360 / p["n_sticks"], G.STICK_Z0 + 1), V(0, 0, 1)) for i in range(p["n_sticks"])]
    for z, n, d in G.OUTER_HOLES:
        cut += radial_holes(G.R_LO - 2, n, d, z, 4, 180 / n)
    for z, n, d, ph in G.INNER_HOLES:
        cut += radial_holes(G.R_LI - 2, n, d, z, 4, ph)
    a, z = G.GLOW
    cut.append(cyl(2.5, 4, polar(G.R_LO - 2, a, z), radial_dir(a)))
    return cut_all(part, cut)


def make_ngv():
    zc = (G.Z_NGV_V0 + G.Z_NGV_V1) / 2
    vanes = union_all(pattern(tilted_plate(G.R_NGV_H - 1.0, G.R_NGV_T + 1.0, zc, p["ngv_len"] + 3, 1.2, p["ngv_angle"]), p["n_ngv"]))
    vanes = vanes.intersect(rev(G.rect(G.R_NGV_H - 0.3, G.R_NGV_T + 0.3, G.Z_NGV_V0 - 1, G.Z_NGV_V1 + 1)))
    part = union_all([rev(G.ngv_hub_profile()), rev(G.ngv_ring_profile()), vanes])
    cut = axial_holes(G.TUNNEL_BOLT_R, 4, p["m3_clear"], G.Z_TUN_E - 1, 6, 45)
    cut += axial_holes(G.R_PCD, p["n_flange_screws"], p["m3_clear"], G.Z_NGV_E - 1, 5, 22.5)
    return cut_all(part, cut)


def make_turbine_wheel():
    rh = p["turb_hub_d"] / 2
    zc = G.Z_TURB + 1 + p["turb_width"] / 2
    blades = union_all(pattern(tilted_plate(rh - 0.5, p["turb_tip_d"] / 2 + 1, zc, p["turb_width"], 1.3, p["turb_blade_angle"]),
                               p["n_turb_blades"]))
    blades = blades.intersect(rev(G.rect(rh - 0.6, p["turb_tip_d"] / 2, G.Z_TURB, G.Z_TURB + p["turb_width"] + 2)))
    return union_all([rev(G.turbine_disk_profile()), blades])


def make_casing():
    a, z = G.GLOW
    body = union_all([rev(G.CASING_TUBE), rev(G.CASING_FRONT_FLANGE), rev(G.CASING_REAR_FLANGE),
                      cyl(4.5, 3.0, polar(G.R_CAS - 0.5, a, z), radial_dir(a))])
    fz = G.CASING_FRONT_FLANGE[0][1]
    rz = G.CASING_REAR_FLANGE[0][1]
    cut = axial_holes(G.R_PCD, p["n_flange_screws"], p["m3_tap"], fz - 1, 5, 22.5)
    cut += axial_holes(G.R_PCD, p["n_flange_screws"], p["m3_tap"], rz - 1, 5, 22.5)
    for fa, fz_ in G.FITTINGS.values():
        cut.append(cyl(2.1, 6, polar(G.R_CASI - 1, fa, fz_), radial_dir(fa)))
    cut.append(cyl(2.5, 8, polar(G.R_CASI - 1, a, z), radial_dir(a)))
    return cut_all(body, cut)


def make_nozzle():
    a, z = G.TC
    struts = pattern(meridional_plate(G.nozzle_strut(), 1.2), 3, 90)
    boss = cyl(3.5, 6, polar(G.R_TSH + 0.5, a, z), radial_dir(a))
    part = union_all([rev(G.nozzle_profile()), rev(G.tail_cone_profile()), boss] + struts)
    cut = axial_holes(G.R_PCD, p["n_flange_screws"], p["m3_clear"], G.Z_NOZ_F - 1, 5, 22.5)
    cut += axial_holes(46.0, p["n_flange_screws"], 10.0, G.Z_NOZ_F - 1, 5, 0.0)   # lightening holes
    cut.append(cyl(0.85, 14, polar(G.R_TSH - 4, a, z), radial_dir(a)))
    return cut_all(part, cut)


def make_fitting(name):
    a, z = G.FITTINGS[name]
    d = radial_dir(a)
    base = polar(G.R_CAS, a, z)
    wall = p["casing_wall"]
    hexb = cq.Workplane(plane_for(base, d)).polygon(6, 7 * 1.1547).extrude(4).val()
    barb = cyl(2.0, 9, base + d * 4, d)
    stub = cyl(2.0, wall + 1.5, base - d * (wall + 1.5), d)
    nut = cq.Workplane(plane_for(base - d * (wall + 2.5), d)).polygon(6, 7 * 1.1547).extrude(1.0).val()
    return union_all([hexb, barb, stub, nut]).cut(cyl(1.0, 20, base - d * 5, d)).clean()


def make_fuel_system():
    """Fuel manifold + needles, gas start ring, lube line."""
    a_f, z_f = G.FITTINGS["fuel"]
    a_g, z_g = G.FITTINGS["gas"]
    a_l, z_l = G.FITTINGS["lube"]
    ring = cq.Solid.makeTorus(G.R_STICK, 1.5, pnt=V(0, 0, z_f), dir=V(0, 0, 1))
    needles = [cyl(0.5, (G.Z_COMB_F + 2) - z_f - 1.0, polar(G.R_STICK, i * 360 / p["n_sticks"], z_f + 1.0), V(0, 0, 1))
               for i in range(p["n_sticks"])]
    feed = cyl(1.5, G.R_CASI - 3.0 - (G.R_STICK + 1.2), polar(G.R_STICK + 1.2, a_f, z_f), radial_dir(a_f))
    fuel = ring.fuse(feed, *needles)
    gas = cq.Solid.makeTorus(G.GAS_RING_R, 1.2, pnt=V(0, 0, z_g), dir=V(0, 0, 1))
    gas = gas.fuse(cyl(1.2, G.R_CASI - 3.0 - (G.GAS_RING_R + 1.0), polar(G.GAS_RING_R + 1.0, a_g, z_g), radial_dir(a_g))).clean()
    lube = cyl(1.25, G.R_CASI - 3.0 - 16.0, polar(16.0, a_l, z_l), radial_dir(a_l))
    return fuel, gas, lube


def make_glow_plug():
    a, z = G.GLOW
    d = radial_dir(a)
    base = polar(G.R_CAS + 3.0, a, z)
    hexb = cq.Workplane(plane_for(base, d)).polygon(6, 10 * 1.1547).extrude(6).val()
    return union_all([hexb, cyl(2.4, 6.0, base - d * 6.0, d), cyl(1.4, 8.0, base - d * 14.0, d), cyl(1.5, 5, base + d * 6, d)])


def make_thermocouple():
    a, z = G.TC
    d = radial_dir(a)
    fit = cq.Workplane(plane_for(polar(G.R_TSH + 6.5, a, z), d)).polygon(6, 8 * 1.1547).extrude(5).val()
    return union_all([cyl(0.75, 18, polar(G.R_TSH - 12, a, z), d), fit, cyl(1.0, 20, polar(G.R_TSH + 11.5, a, z), d)])


def make_comp_nut():
    n = G.COMP_NUT
    cone = cq.Solid.makeCone(n["cone_r0"], n["cone_r1"], n["cone_h"], V(0, 0, n["z0"]), V(0, 0, -1))
    return hex_nut(n["af"], n["h"], p["wheel_bore"], n["z0"]).fuse(cone).clean()


def make_starter_bracket():
    arms = [meridional_plate(G.starter_arm(), 8.0).rotate(V(0, 0, 0), V(0, 0, 1), a) for a in G.STARTER_ANGLES]
    body = union_all([rev(G.STARTER_HUB)] + arms)
    cut = [cyl(p["m3_clear"] / 2, 8, polar(33.0, a, G.STARTER_SCREW_Z), radial_dir(a)) for a in G.STARTER_ANGLES]
    return cut_all(body, cut)


def make_starter_motor():
    return rev(G.STARTER_MOTOR).fuse(cyl(1.5, 8, V(0, 0, G.Z_STARTER), V(0, 0, 1))).clean()


def make_mount_band(zc):
    w, r = G.BAND_W, G.R_CAS
    band = rev(G.rect(r, r + 3, zc - w / 2, zc + w / 2))
    ears = [cq.Solid.makeBox(5, 8, w, V(s, r + 1.0, zc - w / 2)) for s in (-8.0, 3.0)]
    foot = cq.Solid.makeBox(24, p["mount_drop"] - 1.5, w, V(-12, G.Y_PLATE, zc - w / 2))
    gap = cq.Solid.makeBox(6, 10, w + 2, V(-3, r - 2, zc - w / 2 - 1))
    body = union_all([band] + ears + [foot]).cut(gap).clean()
    body = body.cut(cyl(r, w + 2, V(0, 0, zc - w / 2 - 1), V(0, 0, 1))).clean()
    cut = [cyl(p["m3_clear"] / 2, 20, V(-10, r + 5.0, zc), V(1, 0, 0)), cyl(p["m3_tap"] / 2, 10, V(0, G.Y_PLATE - 1, zc), V(0, 1, 0))]
    return cut_all(body, cut)


def make_mount_plate():
    z0, z1 = G.MOUNT_Z[0] - 20, G.MOUNT_Z[1] + 20
    w, t = p["mount_plate_w"], p["mount_plate_t"]
    plate = cq.Solid.makeBox(w, t, z1 - z0, V(-w / 2, G.Y_PLATE - t, z0))
    cut = [cyl(p["mount_hole_d"] / 2, 20, V(x, G.Y_PLATE - 10, z), V(0, 1, 0)) for x in (-w / 2 + 8, w / 2 - 8) for z in (z0 + 8, z1 - 8)]
    cut += [cyl(p["m3_clear"] / 2, 20, V(0, G.Y_PLATE - 10, z), V(0, 1, 0)) for z in G.MOUNT_Z]
    return cut_all(plate, cut)


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
    parts = []

    def add(name, solid, color, material, kind):
        parts.append((name, solid, color, material, kind))

    add("01_intake_cover", make_intake(), AL, "al", "make")
    add("02_compressor_wheel_ENVELOPE", make_compressor_wheel(), TI, "al", "buy")
    add("03_diffuser", make_diffuser(), AL, "al", "make")
    add("04_bearing_tunnel", make_tunnel(), AL, "al", "make")
    add("05_shaft", rev(G.shaft_profile()), STEEL, "steel", "make")
    add("06_bearing_front_608", make_bearing(G.Z_BRG1), STEEL, "steel", "buy")
    add("06_bearing_rear_608", make_bearing(G.Z_SHOULDER2), STEEL, "steel", "buy")
    add("07_front_sleeve", rev(G.SLEEVE_FRONT), STEEL, "steel", "make")
    add("07_rear_sleeve", rev(G.SLEEVE_REAR), STEEL, "steel", "make")
    add("07_rear_bearing_wave_spring", rev(G.WAVE_SPRING), STEEL, "steel", "buy")
    add("08_combustor", make_combustor(), SS, "ss", "make")
    add("09_ngv", make_ngv(), INC, "inc", "make")
    add("10_turbine_wheel_ENVELOPE", make_turbine_wheel(), INC, "inc", "buy")
    add("11_casing", make_casing(), SS, "ss", "make")
    add("12_nozzle", make_nozzle(), SS, "ss", "make")
    add("13_compressor_nut", make_comp_nut(), STEEL, "steel", "make")
    add("13_turbine_nut", hex_nut(G.TURB_NUT["af"], G.TURB_NUT["h"], p["wheel_bore"], G.TURB_NUT["z0"]), STEEL, "steel", "buy")
    fuel, gas, lube = make_fuel_system()
    add("14_fuel_manifold", fuel, BRASS, "ss", "make")
    add("14_gas_ring", gas, BRASS, "ss", "make")
    add("14_lube_line", lube, BRASS, "ss", "make")
    for k in G.FITTINGS:
        add(f"15_fitting_{k}", make_fitting(k), BRASS, "brass", "buy")
    add("16_glow_plug", make_glow_plug(), STEEL, "steel", "buy")
    add("17_thermocouple_K", make_thermocouple(), STEEL, "steel", "buy")
    add("18_starter_bracket", make_starter_bracket(), AL, "al", "make")
    add("18_starter_motor_ENVELOPE", make_starter_motor(), DARK, "other", "buy")
    add("18_starter_cone", rev(G.starter_cone_profile()), DARK, "other", "make")
    for i, zc in enumerate(G.MOUNT_Z):
        add(f"19_mount_band_{i + 1}", make_mount_band(zc), AL, "al", "make")
    add("20_mount_plate", make_mount_plate(), AL, "al", "make")
    for i, (label, d, length, pos, direction) in enumerate(G.fasteners()):
        add(f"99_screw_{i:02d}_{label.replace(' ', '_')}", cap_screw(d, length, vec(pos), vec(direction)), DARK, "steel", "buy")
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
    total = 0.0
    with open(os.path.join(out_dir, "mass_report.csv"), "w") as f:
        f.write("part,make_or_buy,material,mass_g\n")
        for name, solid, _, mat, kind in parts:
            m = solid.Volume() * DENSITY[mat]
            total += m
            f.write(f"{name},{kind},{mat},{m:.1f}\n")
        f.write(f"TOTAL,,,{total:.1f}\n")
    print(f"Estimated dry mass: {total:.0f} g")


def interference_check(parts):
    """Volume overlap between major parts (screws/fittings excluded)."""
    major = [(n, s, s.BoundingBox()) for n, s, *_ in parts if not n.startswith(("99_", "15_"))]
    hits = []
    for i in range(len(major)):
        for j in range(i + 1, len(major)):
            n1, s1, b1 = major[i]
            n2, s2, b2 = major[j]
            if b1.xmax < b2.xmin or b2.xmax < b1.xmin or b1.ymax < b2.ymin or b2.ymax < b1.ymin or \
               b1.zmax < b2.zmin or b2.zmax < b1.zmin:
                continue
            v = s1.intersect(s2).Volume()
            if v > 1.0:
                hits.append((n1, n2, v))
    return hits


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    parts = build()
    export(parts, out)
    report(parts, out)
    if "--check" in sys.argv:
        bad = [n for n, s, *_ in parts if not s.isValid()]
        print("Invalid solids: " + ", ".join(bad) if bad else "All solids valid.")
        hits = interference_check(parts)
        print("Interference (mm^3):" if hits else "No interference above 1 mm^3 between major parts.")
        for h in hits:
            print(f"  {h[0]}  x  {h[1]}: {h[2]:.1f}")
