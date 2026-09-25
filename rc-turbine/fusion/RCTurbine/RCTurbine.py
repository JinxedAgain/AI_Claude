"""
RC micro-turbine: native Autodesk Fusion build.

Builds the whole engine as a parametric Fusion design: one component per part,
real sketches, revolves, extrudes, circular patterns and construction
geometry in the timeline, physical materials, and user parameters.

Run it from Fusion: Utilities > ADD-INS > Scripts and Add-Ins > Scripts > "+"
(or the green plus), pick this folder, then Run. It creates a new design
document. It takes about a minute or two.

Live parameters (Modify > Change Parameters, and the timeline updates):
  blade/vane/screw counts, blade and vane angles, screw hole sizes,
  vaporizer-stick diameter and length, mount plate thickness and hole size.
Everything else (wheel sizes, casing, stations) is set in PARAMS in
turbine_geometry.py; edit it and run this script again for a fresh design.
turbine_geometry.py is the same file the CadQuery/STEP build uses, so both
builds always match.
"""
import importlib
import math
import os
import sys
import traceback

import adsk.core
import adsk.fusion

_HERE = os.path.dirname(os.path.realpath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import turbine_geometry as G  # noqa: E402

MM = 0.1  # the Fusion API works in centimetres

# Parameter units: counts are unitless, angles in degrees, the rest in mm
UNITLESS = {k for k in G.PARAMS if k.startswith("n_")}
ANGLES = {"ngv_angle", "turb_blade_angle"}
EXTRA_PARAMS = {"diff_vane_angle": (22.0, "deg", "Axial diffuser vane angle")}

MATERIALS = {
    "al": ["Aluminum 6061", "Aluminum"],
    "ss": ["Stainless Steel 316", "Stainless Steel", "Steel, Stainless"],
    "inc": ["Nickel Alloy", "Inconel", "Nickel", "Steel, High Strength Low Alloy"],
    "steel": ["Steel, Alloy", "Steel"],
    "brass": ["Brass"],
    "rubber": ["Rubber", "ABS Plastic", "Plastic"],
}


def mm(v):
    return v * MM


def P3(t):
    return adsk.core.Point3D.create(mm(t[0]), mm(t[1]), mm(t[2]))


def V3(t):
    return adsk.core.Vector3D.create(t[0], t[1], t[2])


def VI(expr):
    """ValueInput from an expression string ('3.4 mm', 'n_ngv') or a length in mm."""
    if isinstance(expr, str):
        return adsk.core.ValueInput.createByString(expr)
    return adsk.core.ValueInput.createByReal(mm(expr))


def fmt_mm(v):
    return "{:.4f} mm".format(v)


# ---------------------------------------------------------------------------
# Geometry read-back helpers (kept separate so they are easy to stub in tests)
# ---------------------------------------------------------------------------
def plane_normal(cp):
    n = cp.geometry.normal
    return (n.x, n.y, n.z)


def plane_origin_mm(cp):
    o = cp.geometry.origin
    return (o.x / MM, o.y / MM, o.z / MM)


def profiles_of(sk):
    return [sk.profiles.item(i) for i in range(sk.profiles.count)]


def profile_area(prof):
    return prof.areaProperties().area


def loop_count(prof):
    return prof.profileLoops.count


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    L = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


# ---------------------------------------------------------------------------
# Builder: wraps the Fusion API calls used by every part
# ---------------------------------------------------------------------------
class Builder:
    def __init__(self, design):
        self.design = design
        self.root = design.rootComponent
        self.materials = self._load_materials()

    # ----- components ------------------------------------------------------
    def new_component(self, name, parent=None, material=None):
        parent = parent or self.root
        occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = name
        return occ, comp

    def finish_component(self, comp, material):
        m = self.materials.get(material)
        for i in range(comp.bRepBodies.count):
            b = comp.bRepBodies.item(i)
            if m is not None:
                try:
                    b.material = m
                except Exception:
                    pass
            b.name = comp.name if comp.bRepBodies.count == 1 else "{} {}".format(comp.name, i + 1)

    # ----- planes and axes -------------------------------------------------
    def axial_plane(self, comp, z):
        """Plane normal to the engine axis at height z (mm)."""
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(comp.xYConstructionPlane, VI(z))
        cp = comp.constructionPlanes.add(pi)
        if abs(plane_origin_mm(cp)[2] - z) > 1e-3:
            cp.deleteMe()
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xYConstructionPlane, VI(-z))
            cp = comp.constructionPlanes.add(pi)
        cp.isLightBulbOn = False
        return cp

    def xz_offset_plane(self, comp, y):
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(comp.xZConstructionPlane, VI(y))
        cp = comp.constructionPlanes.add(pi)
        if abs(plane_origin_mm(cp)[1] - y) > 1e-3:
            cp.deleteMe()
            pi = comp.constructionPlanes.createInput()
            pi.setByOffset(comp.xZConstructionPlane, VI(-y))
            cp = comp.constructionPlanes.add(pi)
        cp.isLightBulbOn = False
        return cp

    def meridional_plane(self, comp, a_deg):
        """Plane containing the engine axis and the radial direction at angle a."""
        if abs(a_deg) < 1e-9:
            return comp.xZConstructionPlane
        want = G.radial_dir(a_deg)
        for sgn in (1, -1):
            pi = comp.constructionPlanes.createInput()
            pi.setByAngle(comp.zConstructionAxis, adsk.core.ValueInput.createByReal(sgn * math.radians(a_deg)),
                          comp.xZConstructionPlane)
            cp = comp.constructionPlanes.add(pi)
            if abs(dot(plane_normal(cp), want)) < 1e-6:
                cp.isLightBulbOn = False
                return cp
            cp.deleteMe()
        raise RuntimeError("could not build meridional plane at {} deg".format(a_deg))

    def radial_plane(self, comp, a_deg, dist):
        """Plane normal to the radial direction at angle a, at distance dist (mm) from the axis."""
        want = G.radial_dir(a_deg)
        base = comp.yZConstructionPlane if abs(a_deg) < 1e-9 else None
        for sgn in ((1, -1) if base is None else ()):
            pi = comp.constructionPlanes.createInput()
            pi.setByAngle(comp.zConstructionAxis, adsk.core.ValueInput.createByReal(sgn * math.radians(a_deg)),
                          comp.yZConstructionPlane)
            cp = comp.constructionPlanes.add(pi)
            if abs(abs(dot(plane_normal(cp), want)) - 1.0) < 1e-6:
                base = cp
                break
            cp.deleteMe()
        if base is None:
            raise RuntimeError("could not build radial plane at {} deg".format(a_deg))
        if base is not comp.yZConstructionPlane:
            base.isLightBulbOn = False
        sign = 1.0 if dot(plane_normal(base), want) > 0 else -1.0
        pi = comp.constructionPlanes.createInput()
        pi.setByOffset(base, VI(sign * dist))
        cp = comp.constructionPlanes.add(pi)
        cp.isLightBulbOn = False
        return cp

    def x_axis_at(self, comp, z):
        """Construction axis parallel to X through (0, 0, z): the pivot for tilted blades."""
        sk = comp.sketches.add(comp.xZConstructionPlane)
        sk.name = "blade pivot z={:.1f}".format(z)
        pts = sk.sketchPoints
        a = pts.add(sk.modelToSketchSpace(P3((0, 0, z))))
        b = pts.add(sk.modelToSketchSpace(P3((10, 0, z))))
        sk.isVisible = False
        ai = comp.constructionAxes.createInput()
        ai.setByTwoPoints(a, b)
        ax = comp.constructionAxes.add(ai)
        ax.isLightBulbOn = False
        return ax

    def tilted_plane(self, comp, z, angle_expr):
        ax = self.x_axis_at(comp, z)
        pi = comp.constructionPlanes.createInput()
        pi.setByAngle(ax, VI(angle_expr), comp.xZConstructionPlane)
        cp = comp.constructionPlanes.add(pi)
        cp.isLightBulbOn = False
        return cp

    # ----- sketches --------------------------------------------------------
    def sketch(self, comp, plane, name):
        sk = comp.sketches.add(plane)
        sk.name = name
        return sk

    def polyline(self, sk, model_pts):
        """Closed polyline through model-space points (mm)."""
        lines = sk.sketchCurves.sketchLines
        pts = [sk.modelToSketchSpace(P3(q)) for q in model_pts]
        first = prev = lines.addByTwoPoints(pts[0], pts[1])
        for q in pts[2:]:
            prev = lines.addByTwoPoints(prev.endSketchPoint, q)
        lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)

    def rz_profile_sketch(self, comp, pts_rz, name, a_deg=0.0):
        plane = self.meridional_plane(comp, a_deg)
        sk = self.sketch(comp, plane, name)
        c, s = math.cos(math.radians(a_deg)), math.sin(math.radians(a_deg))
        self.polyline(sk, [(r * c, r * s, z) for r, z in pts_rz])
        return sk

    def circle(self, sk, center_mm, dia):
        """Circle; dia is a number (mm) or a parameter expression, which gets a live dimension."""
        c = sk.modelToSketchSpace(P3(center_mm))
        if isinstance(dia, str):
            circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, mm(1.0))
            circ.centerSketchPoint.isFixed = True
            txt = adsk.core.Point3D.create(c.x + mm(2), c.y + mm(2), 0)
            d = sk.sketchDimensions.addDiameterDimension(circ, txt)
            d.parameter.expression = dia
        else:
            circ = sk.sketchCurves.sketchCircles.addByCenterRadius(c, mm(dia / 2))
        return circ

    def hexagon(self, sk, center_mm, af, frame=((1, 0, 0), (0, 1, 0))):
        """Regular hexagon, across-flats af, in the plane spanned by the two frame vectors."""
        R = af / math.sqrt(3)
        u, v = frame
        pts = []
        for k in range(6):
            t = math.radians(60 * k)
            pts.append(tuple(center_mm[i] + R * (math.cos(t) * u[i] + math.sin(t) * v[i]) for i in range(3)))
        self.polyline(sk, pts)

    def pick(self, sk, mode="largest"):
        profs = profiles_of(sk)
        if mode == "ring":
            rings = [q for q in profs if loop_count(q) > 1]
            if rings:
                return max(rings, key=profile_area)
        if mode == "smallest":
            return min(profs, key=profile_area)
        return max(profs, key=profile_area)

    def all_profiles(self, sk):
        coll = adsk.core.ObjectCollection.create()
        for q in profiles_of(sk):
            coll.add(q)
        return coll

    # ----- features --------------------------------------------------------
    def revolve(self, comp, prof, op, body=None):
        revs = comp.features.revolveFeatures
        ri = revs.createInput(prof, comp.zConstructionAxis, op)
        ri.setAngleExtent(False, adsk.core.ValueInput.createByString("360 deg"))
        if body is not None:
            ri.participantBodies = [body]
        return revs.add(ri)

    def revolve_rz(self, comp, pts_rz, name, op=None, body=None):
        op = op if op is not None else adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        sk = self.rz_profile_sketch(comp, pts_rz, name)
        return self.revolve(comp, self.pick(sk), op, body)

    def extrude_sym(self, comp, prof, length, op, body=None):
        """Symmetric extrude; length is total (number in mm or expression)."""
        ext = comp.features.extrudeFeatures
        ei = ext.createInput(prof, op)
        ei.setSymmetricExtent(VI(length if isinstance(length, str) else fmt_mm(length)), True)
        if body is not None:
            ei.participantBodies = [body]
        return ext.add(ei)

    def pattern(self, comp, feature, qty_expr, bodies=False):
        cps = comp.features.circularPatternFeatures
        ents = adsk.core.ObjectCollection.create()
        ents.add(feature)
        ci = cps.createInput(ents, comp.zConstructionAxis)
        ci.quantity = VI(str(qty_expr))
        ci.totalAngle = adsk.core.ValueInput.createByString("360 deg")
        ci.isSymmetric = False
        if not bodies:
            try:
                ci.patternComputeOption = adsk.fusion.PatternComputeOptions.AdjustPatternCompute
            except Exception:
                pass
        return cps.add(ci)

    def body0(self, comp):
        return comp.bRepBodies.item(0)

    # ----- common operations ----------------------------------------------
    def axial_hole(self, comp, body, center_mm, z_mid, depth, dia, qty=None, name="hole"):
        sk = self.sketch(comp, self.axial_plane(comp, z_mid), name)
        self.circle(sk, (center_mm[0], center_mm[1], z_mid), dia)
        f = self.extrude_sym(comp, self.pick(sk, "smallest"), depth, adsk.fusion.FeatureOperations.CutFeatureOperation, body)
        if qty is not None:
            self.pattern(comp, f, qty)
        return f

    def radial_cyl(self, comp, a_deg, r0, r1, z, dia, op, body=None, qty=None, name="radial"):
        """Cylinder along the radial direction at angle a, from r0 to r1, at height z."""
        rm = (r0 + r1) / 2
        sk = self.sketch(comp, self.radial_plane(comp, a_deg, rm), name)
        self.circle(sk, G.polar(rm, a_deg, z), dia)
        f = self.extrude_sym(comp, self.pick(sk, "smallest"), r1 - r0, op, body)
        if qty is not None:
            self.pattern(comp, f, qty)
        return f

    def tilted_vane(self, comp, zc, r0, r1, length, t, angle_expr, qty_expr, name):
        """Flat vane spanning r0..r1 about a radial pivot at zc, tilted by angle_expr, patterned."""
        cp = self.tilted_plane(comp, zc, angle_expr)
        u = unit(cross(plane_normal(cp), (1.0, 0.0, 0.0)))
        h = length / 2
        pts = [(r0 + u[0] * -h, u[1] * -h, zc + u[2] * -h), (r1 + u[0] * -h, u[1] * -h, zc + u[2] * -h),
               (r1 + u[0] * h, u[1] * h, zc + u[2] * h), (r0 + u[0] * h, u[1] * h, zc + u[2] * h)]
        sk = self.sketch(comp, cp, name)
        self.polyline(sk, pts)
        f = self.extrude_sym(comp, self.pick(sk), t, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        return self.pattern(comp, f, qty_expr)

    def trim_annulus(self, comp, ri, ro, z0, z1, name="trim"):
        self.revolve_rz(comp, G.rect(ri, ro, z0, z1), name, adsk.fusion.FeatureOperations.CutFeatureOperation,
                        self.body0(comp))

    # ----- materials -------------------------------------------------------
    def _load_materials(self):
        app = adsk.core.Application.get()
        found = {}
        try:
            index = {}
            for li in range(app.materialLibraries.count):
                lib = app.materialLibraries.item(li)
                for mi in range(lib.materials.count):
                    m = lib.materials.item(mi)
                    index.setdefault(m.name.lower(), m)
            for key, names in MATERIALS.items():
                for n in names:
                    hit = index.get(n.lower()) or next((m for k, m in index.items() if n.lower() in k), None)
                    if hit is not None:
                        found[key] = hit
                        break
        except Exception:
            pass
        return found


# ---------------------------------------------------------------------------
# Transforms for reused components
# ---------------------------------------------------------------------------
def placement(pos_mm, direction=(0, 0, 1)):
    """Matrix taking local +Z to `direction` and the local origin to pos_mm."""
    m = adsk.core.Matrix3D.create()
    d = unit(direction)
    if d[2] < -0.999999:
        m.setToRotation(math.pi, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Point3D.create(0, 0, 0))
    elif d[2] < 0.999999:
        m.setToRotateTo(adsk.core.Vector3D.create(0, 0, 1), V3(d))
    m.translation = adsk.core.Vector3D.create(mm(pos_mm[0]), mm(pos_mm[1]), mm(pos_mm[2]))
    return m


def set_transform(occ, m):
    try:
        occ.transform2 = m
    except Exception:
        occ.transform = m


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
NEW = None  # filled in run() once adsk is available
JOIN = None
CUT = None
p = G.PARAMS


def part_intake(B):
    _, c = B.new_component("01 Intake cover")
    B.revolve_rz(c, G.intake_profile(), "intake profile")
    b = B.body0(c)
    B.axial_hole(c, b, G.polar(G.R_PCD, 22.5), G.Z_CEX_F - 2, 8, "m3_clear", "n_flange_screws", "casing screw holes")
    for i, (x, y) in enumerate(G.screw_vanes()):
        B.axial_hole(c, b, (x, y), G.Z_CEX_F - 2, 8, "m3_clear", None, "diffuser screw hole {}".format(i + 1))
    a0 = G.STARTER_ANGLES[0]
    B.radial_cyl(c, a0, 28.5, 34.5, G.STARTER_SCREW_Z, "m3_tap", CUT, b, len(G.STARTER_ANGLES), "starter bracket taps")
    return c, "al"


def part_compressor_wheel(B):
    _, c = B.new_component("02 Compressor wheel ENVELOPE (buy)")
    B.revolve_rz(c, G.comp_wheel_profile(), "hub")
    sk = B.rz_profile_sketch(c, G.comp_blade_main(), "main blade")
    B.pattern(c, B.extrude_sym(c, B.pick(sk), 0.9, JOIN), "n_comp_blades")
    a = 180.0 / p["n_comp_blades"]
    sk = B.rz_profile_sketch(c, G.comp_blade_splitter(), "splitter blade", a)
    B.pattern(c, B.extrude_sym(c, B.pick(sk), 0.8, JOIN), "n_comp_blades")
    return c, "al"


def part_diffuser(B):
    _, c = B.new_component("03 Diffuser")
    B.revolve_rz(c, G.diffuser_profile(), "diffuser profile")
    b = B.body0(c)
    tri, z0, z1, _ = G.radial_vane(0)
    zm = (z0 + z1) / 2
    sk = B.sketch(c, B.axial_plane(c, zm), "radial vane")
    B.polyline(sk, [(x, y, zm) for x, y in tri])
    B.pattern(c, B.extrude_sym(c, B.pick(sk), z1 - z0, JOIN), "n_radial_vanes")
    zc = (G.Z_CEX_H + G.Z_AXD_END) / 2
    B.tilted_vane(c, zc, 49.6, G.R_CASI + 1.0, p["axial_diff_len"] - 2, 1.2, "diff_vane_angle", "n_axial_vanes", "axial vane")
    B.trim_annulus(c, G.R_CASI - 0.1, G.R_CASI + 8, G.Z_CEX_H - 1, G.Z_AXD_END + 1, "trim vanes to casing bore")
    for i, (x, y) in enumerate(G.screw_vanes()):
        B.axial_hole(c, b, (x, y), (G.Z_CEX_F + G.Z_CEX_H) / 2 + 2, 12, "m3_tap", None, "intake screw tap {}".format(i + 1))
    B.axial_hole(c, b, G.polar(G.TUNNEL_BOLT_R, 45), G.Z_DIFF_R + 2.5, 8, "m3_tap", 4, "tunnel screw taps")
    return c, "al"


def part_tunnel(B):
    _, c = B.new_component("04 Bearing tunnel")
    B.revolve_rz(c, G.tunnel_profile(), "tunnel profile")
    b = B.body0(c)
    a_l, z_l = G.FITTINGS["lube"]
    B.radial_cyl(c, a_l, 12.0, 16.0, z_l, 6.0, JOIN, None, None, "lube boss")
    fz0, fz1 = G.TUNNEL_FRONT_FLANGE
    rz0, rz1 = G.TUNNEL_REAR_FLANGE
    B.axial_hole(c, b, G.polar(G.TUNNEL_BOLT_R, 45), (fz0 + fz1) / 2, fz1 - fz0 + 2, "m3_clear", 4, "front flange holes")
    B.axial_hole(c, b, G.polar(G.TUNNEL_BOLT_R, 45), (rz0 + rz1) / 2, rz1 - rz0 + 2, "m3_tap", 4, "rear flange taps")
    B.radial_cyl(c, a_l, 8.0, 18.0, z_l, 1.8, CUT, b, None, "lube port")
    return c, "al"


def part_shaft(B):
    _, c = B.new_component("05 Shaft")
    B.revolve_rz(c, G.shaft_profile(), "shaft profile")
    try:  # cosmetic M6x1 threads on both wheel seats
        body = B.body0(c)
        tf = c.features.threadFeatures
        faces = adsk.core.ObjectCollection.create()
        for i in range(body.faces.count):
            f = body.faces.item(i)
            g = f.geometry
            if g.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType and abs(g.radius - mm(G.R_BORE)) < 1e-6:
                faces.add(f)
        info = tf.createThreadInfo(False, "ISO Metric profile", "M6x1", "6g")
        ti = tf.createInput(faces, info)
        ti.isFullLength = True
        ti.isModeled = False
        tf.add(ti)
    except Exception:
        pass
    return c, "steel"


def part_bearings(B):
    occ, c = B.new_component("06 Bearing 608 hybrid (buy)")
    t = p["brg_w"]
    B.revolve_rz(c, G.rect(G.R_SH, G.R_SH + 2.2, 0, t), "inner race")
    B.revolve_rz(c, G.rect(G.R_BRG - 2.2, G.R_BRG, 0, t), "outer race")
    rc = (G.R_SH + G.R_BRG) / 2
    sk = B.sketch(c, c.xZConstructionPlane, "ball")
    ctr = sk.modelToSketchSpace(P3((rc, 0, t / 2)))
    top = sk.modelToSketchSpace(P3((rc, 0, t / 2 + 2.0)))
    bot = sk.modelToSketchSpace(P3((rc, 0, t / 2 - 2.0)))
    side = sk.modelToSketchSpace(P3((rc + 2.0, 0, t / 2)))
    axis = sk.sketchCurves.sketchLines.addByTwoPoints(bot, top)
    sk.sketchCurves.sketchArcs.addByThreePoints(axis.startSketchPoint, side, axis.endSketchPoint)
    revs = c.features.revolveFeatures
    ri = revs.createInput(B.pick(sk), axis, NEW)
    ri.setAngleExtent(False, adsk.core.ValueInput.createByString("360 deg"))
    B.pattern(c, revs.add(ri), 8, bodies=True)
    set_transform(occ, placement((0, 0, G.Z_BRG1)))
    B.root.occurrences.addExistingComponent(c, placement((0, 0, G.Z_SHOULDER2)))
    return c, "steel"


def part_simple(B, name, pts, material):
    _, c = B.new_component(name)
    B.revolve_rz(c, pts, name)
    return c, material


def part_combustor(B):
    _, c = B.new_component("08 Combustor")
    B.revolve_rz(c, G.COMB_PLATE, "front plate")
    B.revolve_rz(c, G.combustor_outer_profile(), "outer liner", JOIN)
    B.revolve_rz(c, G.combustor_inner_profile(), "inner liner", JOIN)
    b = B.body0(c)
    zs = G.STICK_Z0 + p["stick_len"] / 2
    sk = B.sketch(c, B.axial_plane(c, zs), "vaporizer stick")
    B.circle(sk, G.polar(G.R_STICK, 0, zs), "stick_d")
    B.circle(sk, G.polar(G.R_STICK, 0, zs), "stick_d - 0.6 mm")
    B.pattern(c, B.extrude_sym(c, B.pick(sk, "ring"), "stick_len", JOIN), "n_sticks")
    B.axial_hole(c, b, G.polar(G.R_STICK, 0), G.STICK_Z0 + 2.5, 3.0, "stick_d - 0.6 mm", "n_sticks", "stick mouths")
    for k, (z, n, d) in enumerate(G.OUTER_HOLES):
        B.radial_cyl(c, 180.0 / n, G.R_LO - 2, G.R_LO + 2, z, d, CUT, b, n, "outer liner holes row {}".format(k + 1))
    for k, (z, n, d, ph) in enumerate(G.INNER_HOLES):
        B.radial_cyl(c, ph, G.R_LI - 2, G.R_LI + 2, z, d, CUT, b, n, "inner liner holes row {}".format(k + 1))
    a, z = G.GLOW
    B.radial_cyl(c, a, G.R_LO - 2, G.R_LO + 2, z, 5.0, CUT, b, None, "glow plug port")
    return c, "ss"


def part_ngv(B):
    _, c = B.new_component("09 NGV")
    B.revolve_rz(c, G.ngv_hub_profile(), "hub")
    B.revolve_rz(c, G.ngv_ring_profile(), "outer ring + flange")
    zc = (G.Z_NGV_V0 + G.Z_NGV_V1) / 2
    B.tilted_vane(c, zc, G.R_NGV_H - 1.0, G.R_NGV_T + 1.0, p["ngv_len"] + 3, 1.2, "ngv_angle", "n_ngv", "NGV vane")
    b = B.body0(c)
    B.trim_annulus(c, G.R_NGV_T + 1.2, G.R_NGV_T + 6, G.Z_NGV_V0 - 1, G.Z_NGV_V1 + 1, "trim vane tips")
    B.trim_annulus(c, 0.5, G.R_NGV_H - 1.5, G.Z_NGV_V0 - 1, G.Z_NGV_V1 + 1, "trim vane roots")
    B.axial_hole(c, b, G.polar(G.TUNNEL_BOLT_R, 45), G.Z_TUN_E + 1.5, 5, "m3_clear", 4, "hub screw holes")
    B.axial_hole(c, b, G.polar(G.R_PCD, 22.5), G.Z_NGV_E + G.NGV_FLANGE_T / 2, 4, "m3_clear", "n_flange_screws", "flange holes")
    return c, "inc"


def part_turbine_wheel(B):
    _, c = B.new_component("10 Turbine wheel ENVELOPE (buy)")
    B.revolve_rz(c, G.turbine_disk_profile(), "disk")
    rh, rt = p["turb_hub_d"] / 2, p["turb_tip_d"] / 2
    zc = G.Z_TURB + 1 + p["turb_width"] / 2
    B.tilted_vane(c, zc, rh - 0.5, rt + 1, p["turb_width"], 1.3, "turb_blade_angle", "n_turb_blades", "blade")
    B.trim_annulus(c, rt, rt + 6, G.Z_TURB - 1, G.Z_TURB + p["turb_width"] + 3, "trim to tip diameter")
    return c, "inc"


def part_casing(B):
    _, c = B.new_component("11 Casing")
    B.revolve_rz(c, G.CASING_TUBE, "tube")
    B.revolve_rz(c, G.CASING_FRONT_FLANGE, "front flange ring", JOIN)
    B.revolve_rz(c, G.CASING_REAR_FLANGE, "rear flange ring", JOIN)
    b = B.body0(c)
    a, z = G.GLOW
    B.radial_cyl(c, a, G.R_CAS - 0.5, G.R_CAS + 2.5, z, 9.0, JOIN, None, None, "glow plug boss")
    fz = G.CASING_FRONT_FLANGE[0][1]
    rz = G.CASING_REAR_FLANGE[0][1]
    B.axial_hole(c, b, G.polar(G.R_PCD, 22.5), fz + 1.5, 5, "m3_tap", "n_flange_screws", "front flange taps")
    B.axial_hole(c, b, G.polar(G.R_PCD, 22.5), rz + 1.5, 5, "m3_tap", "n_flange_screws", "rear flange taps")
    for name, (fa, fz_) in G.FITTINGS.items():
        B.radial_cyl(c, fa, G.R_CASI - 1, G.R_CASI + 5, fz_, 4.2, CUT, b, None, name + " fitting hole")
    B.radial_cyl(c, a, G.R_CASI - 1, G.R_CASI + 7, z, 5.0, CUT, b, None, "glow plug hole")
    return c, "ss"


def part_nozzle(B):
    _, c = B.new_component("12 Nozzle")
    B.revolve_rz(c, G.nozzle_profile(), "nozzle shell")
    B.revolve_rz(c, G.tail_cone_profile(), "tail cone")
    sk = B.rz_profile_sketch(c, G.nozzle_strut(), "strut", 90.0)
    B.pattern(c, B.extrude_sym(c, B.pick(sk), 1.2, JOIN), 3)
    a, z = G.TC
    B.radial_cyl(c, a, G.R_TSH + 0.5, G.R_TSH + 6.5, z, 7.0, JOIN, None, None, "thermocouple boss")
    b = B.body0(c)
    zf = G.Z_NOZ_F + G.NOZ_FLANGE_T / 2
    B.axial_hole(c, b, G.polar(G.R_PCD, 22.5), zf, 4, "m3_clear", "n_flange_screws", "flange holes")
    B.axial_hole(c, b, G.polar(46.0, 0), zf, 4, 10.0, "n_flange_screws", "lightening holes")
    B.radial_cyl(c, a, G.R_TSH - 4, G.R_TSH + 10, z, 1.7, CUT, b, None, "thermocouple hole")
    return c, "ss"


def part_nuts(B):
    n = G.COMP_NUT
    _, c = B.new_component("13 Compressor nut")
    zm = n["z0"] + n["h"] / 2
    sk = B.sketch(c, B.axial_plane(c, zm), "hex")
    B.hexagon(sk, (0, 0, zm), n["af"])
    B.circle(sk, (0, 0, zm), p["wheel_bore"])
    B.extrude_sym(c, B.pick(sk, "ring"), n["h"], NEW)
    B.revolve_rz(c, [(0, n["z0"]), (n["cone_r0"], n["z0"]), (n["cone_r1"], n["z0"] - n["cone_h"]), (0, n["z0"] - n["cone_h"])],
                 "starter cone", JOIN)
    B.finish_component(c, "steel")
    t = G.TURB_NUT
    _, c2 = B.new_component("13 Turbine nut M6 (buy)")
    zm = t["z0"] + t["h"] / 2
    sk = B.sketch(c2, B.axial_plane(c2, zm), "hex")
    B.hexagon(sk, (0, 0, zm), t["af"])
    B.circle(sk, (0, 0, zm), p["wheel_bore"])
    B.extrude_sym(c2, B.pick(sk, "ring"), t["h"], NEW)
    return c2, "steel"


def part_fuel_system(B):
    a_f, z_f = G.FITTINGS["fuel"]
    _, c = B.new_component("14 Fuel manifold")
    sk = B.sketch(c, c.xZConstructionPlane, "ring section")
    B.circle(sk, (G.R_STICK, 0, z_f), 3.0)
    B.revolve(c, B.pick(sk), NEW)
    z0, z1 = z_f + 1.0, G.Z_COMB_F + 2
    sk = B.sketch(c, B.axial_plane(c, (z0 + z1) / 2), "needle")
    B.circle(sk, G.polar(G.R_STICK, 0, (z0 + z1) / 2), 1.0)
    B.pattern(c, B.extrude_sym(c, B.pick(sk), z1 - z0, JOIN), "n_sticks")
    B.radial_cyl(c, a_f, G.R_STICK + 1.2, G.R_CASI - 3.0, z_f, 3.0, JOIN, None, None, "feed tube")
    B.finish_component(c, "ss")

    a_g, z_g = G.FITTINGS["gas"]
    _, c = B.new_component("14 Start gas ring")
    sk = B.sketch(c, c.xZConstructionPlane, "ring section")
    B.circle(sk, (G.GAS_RING_R, 0, z_g), 2.4)
    B.revolve(c, B.pick(sk), NEW)
    B.radial_cyl(c, a_g, G.GAS_RING_R + 1.0, G.R_CASI - 3.0, z_g, 2.4, JOIN, None, None, "feed tube")
    B.finish_component(c, "ss")

    a_l, z_l = G.FITTINGS["lube"]
    _, c = B.new_component("14 Lube line")
    B.radial_cyl(c, a_l, 16.0, G.R_CASI - 3.0, z_l, 2.5, NEW, None, None, "lube tube")
    return c, "ss"


def hex_prism(B, c, z_mid, af, h, op):
    sk = B.sketch(c, B.axial_plane(c, z_mid), "hex")
    B.hexagon(sk, (0, 0, z_mid), af)
    return B.extrude_sym(c, B.pick(sk), h, op)


def part_fittings(B):
    occ, c = B.new_component("15 Bulkhead barb fitting M5 (buy)")
    w = p["casing_wall"]
    B.revolve_rz(c, G.rect(1.0, 2.0, -(w + 1.5), 13.0), "barb and stub")
    hex_prism(B, c, 2.0, 7.0, 4.0, JOIN)
    hex_prism(B, c, -(w + 2.0), 7.0, 1.0, JOIN)
    B.trim_annulus(c, 0.0, 1.0, -(w + 3), 14, "bore")
    items = list(G.FITTINGS.items())
    for i, (_, (a, z)) in enumerate(items):
        m = placement(G.polar(G.R_CAS, a, z), G.radial_dir(a))
        if i == 0:
            set_transform(occ, m)
        else:
            B.root.occurrences.addExistingComponent(c, m)
    return c, "brass"


def part_glow_plug(B):
    occ, c = B.new_component("16 Glow plug (buy)")
    B.revolve_rz(c, [(0, -14), (1.4, -14), (1.4, -6), (2.4, -6), (2.4, 0), (0, 0)], "thread and element")
    hex_prism(B, c, 3.0, 10.0, 6.0, JOIN)
    B.revolve_rz(c, G.rect(0.0, 1.5, 6.0, 11.0), "terminal", JOIN)
    a, z = G.GLOW
    set_transform(occ, placement(G.polar(G.R_CAS + 3.0, a, z), G.radial_dir(a)))
    return c, "steel"


def part_thermocouple(B):
    occ, c = B.new_component("17 Thermocouple K 1.5 mm (buy)")
    B.revolve_rz(c, [(0, 0), (0.75, 0), (0.75, 18.5), (1.0, 18.5), (1.0, 43.5), (0, 43.5)], "probe and lead")
    hex_prism(B, c, 21.0, 8.0, 5.0, JOIN)
    a, z = G.TC
    set_transform(occ, placement(G.polar(G.R_TSH - 12, a, z), G.radial_dir(a)))
    return c, "steel"


def part_starter(B):
    _, c = B.new_component("18 Starter bracket")
    B.revolve_rz(c, G.STARTER_HUB, "hub")
    sk = B.rz_profile_sketch(c, G.starter_arm(), "arm", G.STARTER_ANGLES[0])
    B.pattern(c, B.extrude_sym(c, B.pick(sk), 8.0, JOIN), len(G.STARTER_ANGLES))
    B.radial_cyl(c, G.STARTER_ANGLES[0], 29.0, 37.0, G.STARTER_SCREW_Z, "m3_clear", CUT, B.body0(c),
                 len(G.STARTER_ANGLES), "screw holes")
    B.finish_component(c, "al")
    _, c = B.new_component("18 Starter motor ENVELOPE (buy)")
    B.revolve_rz(c, G.STARTER_MOTOR, "can")
    B.revolve_rz(c, G.rect(0.0, 1.5, G.Z_STARTER, G.Z_STARTER + 8), "shaft", JOIN)
    B.finish_component(c, "steel")
    _, c = B.new_component("18 Starter clutch cone")
    B.revolve_rz(c, G.starter_cone_profile(), "cone")
    return c, "rubber"


def part_mount(B):
    occ, c = B.new_component("19 Mount band")
    w, r = G.BAND_W, G.R_CAS
    B.revolve_rz(c, G.rect(r, r + 3, -w / 2, w / 2), "band")
    sk = B.sketch(c, c.xYConstructionPlane, "ears and foot")
    for s in (-8.0, 3.0):
        B.polyline(sk, [(s, r + 1, 0), (s + 5, r + 1, 0), (s + 5, r + 9, 0), (s, r + 9, 0)])
    yf = G.Y_PLATE + p["mount_drop"] - 1.5
    B.polyline(sk, [(-12, G.Y_PLATE, 0), (12, G.Y_PLATE, 0), (12, yf, 0), (-12, yf, 0)])
    B.extrude_sym(c, B.all_profiles(sk), w, JOIN)
    b = B.body0(c)
    sk = B.sketch(c, c.xYConstructionPlane, "clamp gap")
    B.polyline(sk, [(-3, r - 2, 0), (3, r - 2, 0), (3, r + 10, 0), (-3, r + 10, 0)])
    B.extrude_sym(c, B.pick(sk), w + 2, CUT, b)
    B.trim_annulus(c, 0.0, r, -w / 2 - 1, w / 2 + 1, "casing seat")
    sk = B.sketch(c, c.yZConstructionPlane, "clamp screw hole")
    B.circle(sk, (0, r + 5, 0), "m3_clear")
    B.extrude_sym(c, B.pick(sk, "smallest"), 20.0, CUT, b)
    sk = B.sketch(c, B.xz_offset_plane(c, G.Y_PLATE + 4), "plate screw tap")
    B.circle(sk, (0, G.Y_PLATE + 4, 0), "m3_tap")
    B.extrude_sym(c, B.pick(sk, "smallest"), 10.0, CUT, b)
    set_transform(occ, placement((0, 0, G.MOUNT_Z[0])))
    for zc in G.MOUNT_Z[1:]:
        B.root.occurrences.addExistingComponent(c, placement((0, 0, zc)))
    B.finish_component(c, "al")

    _, c = B.new_component("20 Mount plate")
    t, wpl = p["mount_plate_t"], p["mount_plate_w"]
    z0, z1 = G.MOUNT_Z[0] - 20, G.MOUNT_Z[-1] + 20
    ym = G.Y_PLATE - t / 2
    plane = B.xz_offset_plane(c, ym)
    sk = B.sketch(c, plane, "plate")
    B.polyline(sk, [(-wpl / 2, ym, z0), (wpl / 2, ym, z0), (wpl / 2, ym, z1), (-wpl / 2, ym, z1)])
    B.extrude_sym(c, B.pick(sk), "mount_plate_t", NEW)
    b = B.body0(c)
    sk = B.sketch(c, plane, "airframe holes")
    for x in (-wpl / 2 + 8, wpl / 2 - 8):
        for z in (z0 + 8, z1 - 8):
            B.circle(sk, (x, ym, z), "mount_hole_d")
    for z in G.MOUNT_Z:
        B.circle(sk, (0, ym, z), "m3_clear")
    ext = c.features.extrudeFeatures
    holes = adsk.core.ObjectCollection.create()
    for q in profiles_of(sk):
        if loop_count(q) == 1 and profile_area(q) < mm(10) * mm(10):
            holes.add(q)
    ei = ext.createInput(holes, CUT)
    ei.setSymmetricExtent(adsk.core.ValueInput.createByString("mount_plate_t + 2 mm"), True)
    ei.participantBodies = [b]
    ext.add(ei)
    return c, "al"


def part_fasteners(B):
    fo, fc = B.new_component("Fasteners")
    made = {}
    for label, d, length, pos, direction in G.fasteners():
        size = label.split()[0]
        m = placement(pos, direction)
        if size not in made:
            occ = fc.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            c = occ.component
            c.name = "ISO 4762 {} socket head cap screw".format(size)
            hd, hh, key = 1.6 * d + 0.7, float(d), 0.8 * d + 0.05
            B.revolve_rz(c, [(0, -hh), (hd / 2, -hh), (hd / 2, 0), (d / 2, 0), (d / 2, length), (0, length)], "screw")
            sk = B.sketch(c, B.axial_plane(c, -hh + 0.3 * hh), "socket")
            B.hexagon(sk, (0, 0, -hh + 0.3 * hh), key)
            B.extrude_sym(c, B.pick(sk), 0.6 * hh, CUT, B.body0(c))
            B.finish_component(c, "steel")
            set_transform(occ, m)
            made[size] = c
        else:
            fc.occurrences.addExistingComponent(made[size], m)
    return fc, None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def add_user_parameters(design):
    ups = design.userParameters
    for k, v in G.PARAMS.items():
        if k in UNITLESS:
            ups.add(k, adsk.core.ValueInput.createByString(str(int(v))), "", "turbine_geometry.PARAMS")
        elif k in ANGLES:
            ups.add(k, adsk.core.ValueInput.createByString("{} deg".format(v)), "deg", "turbine_geometry.PARAMS")
        else:
            ups.add(k, adsk.core.ValueInput.createByString(fmt_mm(v)), "mm", "turbine_geometry.PARAMS")
    for k, (v, unit_, note) in EXTRA_PARAMS.items():
        ups.add(k, adsk.core.ValueInput.createByString("{} {}".format(v, unit_)), unit_, note)


PARTS = [
    ("Intake cover", part_intake),
    ("Compressor wheel", part_compressor_wheel),
    ("Diffuser", part_diffuser),
    ("Bearing tunnel", part_tunnel),
    ("Shaft", part_shaft),
    ("Bearings", part_bearings),
    ("Front sleeve", lambda B: part_simple(B, "07 Front sleeve", G.SLEEVE_FRONT, "steel")),
    ("Rear sleeve", lambda B: part_simple(B, "07 Rear sleeve", G.SLEEVE_REAR, "steel")),
    ("Wave spring", lambda B: part_simple(B, "07 Rear bearing wave spring (buy)", G.WAVE_SPRING, "steel")),
    ("Combustor", part_combustor),
    ("NGV", part_ngv),
    ("Turbine wheel", part_turbine_wheel),
    ("Casing", part_casing),
    ("Nozzle", part_nozzle),
    ("Nuts", part_nuts),
    ("Fuel, gas and lube lines", part_fuel_system),
    ("Fittings", part_fittings),
    ("Glow plug", part_glow_plug),
    ("Thermocouple", part_thermocouple),
    ("Starter", part_starter),
    ("Mount", part_mount),
    ("Fasteners", part_fasteners),
]


def build(design, progress=None):
    """Build every part; returns a list of (part, error-or-None)."""
    global NEW, JOIN, CUT
    NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
    CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
    add_user_parameters(design)
    B = Builder(design)
    results = []
    for i, (label, fn) in enumerate(PARTS):
        if progress is not None:
            progress(i, label)
        try:
            comp, material = fn(B)
            if material:
                B.finish_component(comp, material)
            results.append((label, None))
        except Exception:
            results.append((label, traceback.format_exc(limit=3)))
        adsk.doEvents()
    try:
        design.snapshots.add()  # capture positions of the moved components
    except Exception:
        pass
    return results


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        importlib.reload(G)  # pick up PARAMS edits without restarting Fusion
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        try:
            design.rootComponent.name = "RC micro-turbine"
        except Exception:
            pass
        pd = ui.createProgressDialog()
        pd.show("RC micro-turbine", "Building %v of %m: ...", 0, len(PARTS), 0)

        def progress(i, label):
            pd.progressValue = i
            pd.message = "Building {} ({} of {})".format(label, i + 1, len(PARTS))

        results = build(design, progress)
        pd.hide()
        app.activeViewport.fit()
        failed = [(k, e) for k, e in results if e]
        if failed:
            msg = "Built {} of {} parts. These failed:\n\n".format(len(results) - len(failed), len(results))
            msg += "\n\n".join("{}:\n{}".format(k, e.strip().splitlines()[-1]) for k, e in failed)
            ui.messageBox(msg, "RC micro-turbine")
        else:
            ui.messageBox("Built all {} parts.\n\nChange counts, angles and hole sizes in "
                          "Modify > Change Parameters.".format(len(results)), "RC micro-turbine")
    except Exception:
        ui.messageBox("Failed:\n{}".format(traceback.format_exc()))
