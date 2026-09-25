"""
Offline logic test for RCTurbine.py (no Fusion needed).

Fusion's `adsk` modules only exist inside Fusion, so this installs a small
fake: construction planes carry real geometry (so the plane-orientation
checks in the script are exercised), everything else records calls. It runs
the full build under both possible sign conventions for "plane at angle"
and checks that every part builds, that planes land where they should, and
that sketch points sit on their sketch planes.

Run:  python test_rcturbine_logic.py
"""
import math
import os
import sys
import types
from unittest.mock import MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "RCTurbine"))


# ---------------------------------------------------------------------------
# Fake adsk
# ---------------------------------------------------------------------------
class VI:
    def __init__(self, v=None, e=None):
        self.v, self.e = v, e

    def real(self, param_angles):
        if self.v is not None:
            return self.v
        e = self.e.strip()
        if e.endswith("deg"):
            return math.radians(float(e[:-3]))
        if e in param_angles:
            return math.radians(param_angles[e])
        raise ValueError("unexpected angle expression " + e)


class Pt:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


def rot(v, axis, ang):
    """Rodrigues rotation of v about unit axis."""
    c, s = math.cos(ang), math.sin(ang)
    ax, ay, az = axis
    d = v[0] * ax + v[1] * ay + v[2] * az
    cr = (ay * v[2] - az * v[1], az * v[0] - ax * v[2], ax * v[1] - ay * v[0])
    return tuple(v[i] * c + cr[i] * s + axis[i] * d * (1 - c) for i in range(3))


class Plane:
    def __init__(self, normal, origin, name=""):
        self.normal, self.origin, self.name = normal, origin, name
        self.isLightBulbOn = True
        self.deleted = False

    @property
    def geometry(self):
        # Fusion reports geometry in centimetres
        return types.SimpleNamespace(normal=Pt(*self.normal), origin=Pt(*(c * 0.1 for c in self.origin)))

    def deleteMe(self):
        self.deleted = True


class Axis:
    def __init__(self, direction, point):
        self.direction, self.point = direction, point
        self.isLightBulbOn = True


class PlaneInput:
    def __init__(self, env):
        self.env, self.kind = env, None

    def setByOffset(self, base, value):
        self.kind, self.base, self.value = "offset", base, value

    def setByAngle(self, axis, angle, planar):
        self.kind, self.axis, self.angle, self.planar = "angle", axis, angle, planar


class Planes:
    def __init__(self, env):
        self.env, self.items = env, []

    def createInput(self):
        return PlaneInput(self.env)

    def add(self, inp):
        if inp.kind == "offset":
            d = inp.value.v / 0.1  # cm -> mm
            n = inp.base.normal
            pl = Plane(n, tuple(inp.base.origin[i] + n[i] * d for i in range(3)))
        else:
            ang = inp.angle.real(self.env.angles) * self.env.sign
            n = rot(inp.planar.normal, inp.axis.direction, ang)
            pl = Plane(n, inp.axis.point)
        self.items.append(pl)
        return pl


class Sketch:
    def __init__(self, plane, env):
        self.plane, self.env = plane, env
        self.name = ""
        self.isVisible = True
        self.profiles = MagicMock()
        self.sketchPoints = MagicMock()
        self.sketchPoints.add = lambda p: types.SimpleNamespace(pos=p)
        self.sketchCurves = MagicMock()
        self.sketchDimensions = MagicMock()

    def modelToSketchSpace(self, p):
        # every point we sketch must lie on the sketch plane
        o, n = self.plane.origin, self.plane.normal
        dist = ((p.x / 0.1 - o[0]) * n[0] + (p.y / 0.1 - o[1]) * n[1] + (p.z / 0.1 - o[2]) * n[2])
        if abs(dist) > 1e-6:
            self.env.off_plane.append((self.name, dist))
        return p


class Sketches:
    def __init__(self, env):
        self.env = env

    def add(self, plane):
        return Sketch(plane, self.env)


class Axes:
    def createInput(self):
        return types.SimpleNamespace(setByTwoPoints=lambda a, b: setattr(self, "_pts", (a, b)))

    def add(self, inp):
        a, b = self._pts
        pa = (a.pos.x / 0.1, a.pos.y / 0.1, a.pos.z / 0.1)
        pb = (b.pos.x / 0.1, b.pos.y / 0.1, b.pos.z / 0.1)
        d = tuple(pb[i] - pa[i] for i in range(3))
        L = math.sqrt(sum(x * x for x in d))
        return Axis(tuple(x / L for x in d), pa)


class Comp:
    def __init__(self, env):
        self.name = ""
        self.env = env
        env.comps.append(self)
        self.xYConstructionPlane = Plane((0, 0, 1), (0, 0, 0), "XY")
        self.xZConstructionPlane = Plane((0, env.xz_sign, 0), (0, 0, 0), "XZ")
        self.yZConstructionPlane = Plane((1, 0, 0), (0, 0, 0), "YZ")
        self.zConstructionAxis = Axis((0, 0, 1), (0, 0, 0))
        self.constructionPlanes = Planes(env)
        self.constructionAxes = Axes()
        self.sketches = Sketches(env)
        self.features = MagicMock()
        self.bRepBodies = MagicMock()
        self.bRepBodies.count = 1
        self.occurrences = Occs(env)


class Occs:
    def __init__(self, env):
        self.env = env

    def addNewComponent(self, m):
        return types.SimpleNamespace(component=Comp(self.env), transform2=None)

    def addExistingComponent(self, comp, m):
        self.env.instances.append(comp.name)
        return types.SimpleNamespace(component=comp)


class Env:
    def __init__(self, sign, xz_sign, angles):
        self.sign, self.xz_sign, self.angles = sign, xz_sign, angles
        self.comps, self.instances, self.off_plane = [], [], []


def install_fake_adsk():
    core, fusion = MagicMock(), MagicMock()
    core.ValueInput.createByReal = lambda v: VI(v=v)
    core.ValueInput.createByString = lambda e: VI(e=e)
    core.Point3D.create = lambda x, y, z: Pt(x, y, z)
    adsk = types.ModuleType("adsk")
    adsk.core, adsk.fusion = core, fusion
    adsk.doEvents = lambda: None
    sys.modules["adsk"], sys.modules["adsk.core"], sys.modules["adsk.fusion"] = adsk, core, fusion


def run_case(sign, xz_sign):
    install_fake_adsk()
    import importlib
    import RCTurbine as R
    importlib.reload(R)
    G = R.G
    angles = {"ngv_angle": G.PARAMS["ngv_angle"], "turb_blade_angle": G.PARAMS["turb_blade_angle"],
              "diff_vane_angle": R.EXTRA_PARAMS["diff_vane_angle"][0]}
    env = Env(sign, xz_sign, angles)
    R.profiles_of = lambda sk: [MagicMock()]
    R.profile_area = lambda q: 1.0
    R.loop_count = lambda q: 2
    design = MagicMock()
    design.rootComponent = Comp(env)
    results = R.build(design)
    failed = [(k, e) for k, e in results if e]
    return R, env, results, failed


if __name__ == "__main__":
    ok = True
    for sign in (1, -1):
        for xz_sign in (1, -1):
            R, env, results, failed = run_case(sign, xz_sign)
            live = [pl for c in env.comps for pl in c.constructionPlanes.items if not pl.deleted]
            print("angle sign {:+d}, XZ normal {:+d}: {} parts, {} failed, {} planes, {} components, "
                  "{} reused instances, {} off-plane sketch points".format(
                      sign, xz_sign, len(results), len(failed), len(live), len(env.comps),
                      len(env.instances), len(env.off_plane)))
            for k, e in failed:
                ok = False
                print("  FAILED", k, "\n", e)
            if env.off_plane:
                ok = False
                print("  off-plane:", env.off_plane[:5])
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
