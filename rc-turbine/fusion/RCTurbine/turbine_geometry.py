"""
Shared geometry for the RC micro-turbine.

Pure Python (no CAD imports), used by both builders:
  - fusion/RCTurbine/RCTurbine.py   (Autodesk Fusion API, native timeline)
  - cad/rc_turbine.py               (CadQuery, STEP/STL export)

Units: millimetres. Engine axis = +Z, fittings side = +Y. Every size that
matters is in PARAMS; stations and profiles below are derived from it.
Profiles are closed polylines of (r, z) points revolved about the Z axis.
"""
import math

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
    # Compressor / turbine placeholders
    n_comp_blades=7,
    # NGV / nozzle
    n_ngv=19, ngv_angle=-58.0, n_turb_blades=25, turb_blade_angle=38.0, ngv_len=10.0,
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
R_CAS = p["casing_od"] / 2
R_CASI = R_CAS - p["casing_wall"]
R_FL = p["flange_od"] / 2
R_PCD = p["flange_pcd"] / 2
R_TIP = p["comp_tip_d"] / 2
R_IND = p["comp_inducer_d"] / 2
R_BORE = p["wheel_bore"] / 2
R_SH = p["brg_id"] / 2
R_BRG = p["brg_od"] / 2
CL = p["tip_clearance"]

Z_IND = 14.0                               # compressor inducer face
Z_CEX_F = Z_IND + p["comp_len"] - p["comp_exit_width"]   # exducer shroud edge
Z_CEX_H = Z_IND + p["comp_len"]            # exducer hub edge
Z_CBACK = Z_CEX_H + p["comp_back_t"]       # wheel back face
Z_DIFF_R = Z_CBACK + 0.5                   # diffuser plate front (inner zone)
Z_DIFF_B = Z_DIFF_R + 5.0                  # diffuser plate rear face
Z_AXD_END = Z_CEX_H + p["axial_diff_len"]  # end of axial diffuser
Z_BRG1 = Z_DIFF_B                          # front bearing front face
Z_SHOULDER1 = Z_BRG1 + p["brg_w"]
Z_SHOULDER2 = Z_SHOULDER1 + p["brg_span"]
Z_BRG2_E = Z_SHOULDER2 + p["brg_w"]
Z_TUN_E = Z_BRG2_E                         # tunnel rear face
Z_COMB_F = Z_AXD_END + 12.0                # combustor front plate
Z_OCONE = Z_COMB_F + p["comb_len"]         # outer liner cone start
Z_NGV_F = Z_TUN_E + 5.0
Z_NGV_V0 = Z_NGV_F + 4.0
Z_NGV_V1 = Z_NGV_V0 + p["ngv_len"]
Z_NGV_E = Z_NGV_V1 + 2.0                   # NGV rear / flange front
Z_TURB = Z_NGV_E + 3.0                     # turbine wheel front face
Z_TURB_E = Z_TURB + p["turb_width"] + 2.0  # turbine hub rear face
NGV_FLANGE_T = 1.5
NOZ_T = 0.8
NOZ_FLANGE_T = 2.0
Z_NOZ_F = Z_NGV_E + NGV_FLANGE_T           # nozzle flange front (clamps the NGV flange)
NOZ_EXIT_Z = Z_TURB_E + p["nozzle_len"]
R_LO = p["liner_od"] / 2
R_LI = p["liner_id_inner"] / 2
R_STICK = (R_LI + R_LO) / 2
R_NGV_H = p["turb_hub_d"] / 2 + 0.2
R_NGV_T = p["turb_tip_d"] / 2 + CL + 0.2
R_TSH = p["turb_tip_d"] / 2 + CL          # turbine shroud radius

# Fittings on the casing: name -> (angle deg, z)
FITTINGS = {"fuel": (90.0, Z_COMB_F - 8), "gas": (70.0, Z_COMB_F - 5), "lube": (110.0, Z_COMB_F - 2.5)}
GAS_RING_R = 42.0
GLOW = (200.0, Z_COMB_F + 15)              # glow plug: angle, z
TC = (90.0, Z_TURB_E + 21)                 # thermocouple: angle, z
STARTER_ANGLES = (90.0, 210.0, 330.0)
Z_STARTER = -34.0
MOUNT_Z = (Z_COMB_F + 28, Z_NGV_E - 16)
Y_PLATE = -(R_CAS + p["mount_drop"])
BAND_W = 12.0

# Liner air holes: (z, count, diameter, phase deg) on the outer and inner liners
OUTER_HOLES = [(Z_COMB_F + 12, 18, 3.0), (Z_COMB_F + 32, 12, 4.0), (Z_COMB_F + 58, 10, 6.0)]
INNER_HOLES = [(Z_COMB_F + 18, 12, 2.5, 0.0), (Z_COMB_F + 45, 8, 4.0, 22.5)]

# Compressor shroud and hub curves (wheel side), (r, z)
SHROUD = [(R_IND, Z_IND), (R_IND + 0.2, Z_IND + 4), (R_IND + 1.0, Z_IND + 8), (R_IND + 3.0, Z_IND + 12),
          (R_IND + 6.0, Z_IND + 15), (R_TIP, Z_CEX_F)]
HUB = [(R_BORE + 3.0, Z_IND), (R_BORE + 4.0, Z_IND + 6), (R_BORE + 8.0, Z_IND + 12), (R_BORE + 16.0, Z_IND + 17.5),
       (R_TIP, Z_CEX_H)]

RADIAL_VANE_SCREW_R = 46.0
N_DIFF_SCREWS = 4


def polar(r, a_deg, z=0.0):
    a = math.radians(a_deg)
    return (r * math.cos(a), r * math.sin(a), z)


def radial_dir(a_deg):
    a = math.radians(a_deg)
    return (math.cos(a), math.sin(a), 0.0)


# ---------------------------------------------------------------------------
# Revolve profiles (r, z)
# ---------------------------------------------------------------------------
def intake_profile():
    inner = [(29.0, -4.0), (25.5, 0.0), (23.8, 5.0), (23.0, 10.0)] + [(r + CL, z) for r, z in SHROUD]
    return inner + [(R_FL, Z_CEX_F), (R_FL, Z_CEX_F - 4), (43.0, Z_CEX_F - 4), (38.5, 24.0), (35.0, 18.0),
                    (33.5, 10.0), (32.5, 2.0), (31.8, -2.5), (30.3, -4.4)]


def comp_wheel_profile():
    return [(R_BORE, Z_IND)] + HUB + [(R_TIP, Z_CBACK), (R_BORE, Z_CBACK)]


def comp_blade_main():
    return SHROUD + list(reversed([(r - 0.4, z) for r, z in HUB]))


def comp_blade_splitter():
    mid = 3
    return SHROUD[mid:] + list(reversed([(r - 0.4, z) for r, z in HUB[mid - 1:]]))


def diffuser_profile():
    return [(R_BRG, Z_DIFF_R), (R_TIP + 1.0, Z_DIFF_R), (R_TIP + 1.0, Z_CEX_H), (50.0, Z_CEX_H), (50.0, Z_AXD_END),
            (48.0, Z_AXD_END), (48.0, Z_DIFF_B), (R_BRG, Z_DIFF_B)]


def radial_vane(i):
    """Wedge vane of the radial diffuser. Returns (xy triangle, z0, z1, screw xy)."""
    n = p["n_radial_vanes"]
    a0 = i * 360 / n
    r0, r1 = R_TIP + 1.5, 49.5
    le, te0, te1 = math.radians(a0), math.radians(a0 + 7), math.radians(a0 + 15)
    tri = [(r0 * math.cos(le), r0 * math.sin(le)), (r1 * math.cos(te0), r1 * math.sin(te0)),
           (r1 * math.cos(te1), r1 * math.sin(te1))]
    f = (RADIAL_VANE_SCREW_R - r0) / (r1 - r0)
    s = polar(RADIAL_VANE_SCREW_R, a0 + f * 11)
    return tri, Z_CEX_F + 0.05, Z_CEX_H, (s[0], s[1])


def screw_vanes():
    n = p["n_radial_vanes"]
    return [radial_vane(i)[3] for i in range(0, n, n // N_DIFF_SCREWS)]


def tunnel_profile():
    fl1, fl2 = Z_BRG1 + 4, Z_TUN_E - 3
    return [(R_BRG, Z_BRG1), (19.5, Z_BRG1), (19.5, fl1), (13.0, fl1), (13.0, fl2), (19.5, fl2), (19.5, Z_TUN_E),
            (R_BRG, Z_TUN_E), (R_BRG, Z_SHOULDER2 - 1.0), (9.5, Z_SHOULDER2 - 1.0), (9.5, Z_SHOULDER1),
            (R_BRG, Z_SHOULDER1)]


TUNNEL_FRONT_FLANGE = (Z_BRG1, Z_BRG1 + 4)
TUNNEL_REAR_FLANGE = (Z_TUN_E - 3, Z_TUN_E)
TUNNEL_BOLT_R = 16.5


def shaft_profile():
    z_front = Z_IND - 5.0
    return [(0, z_front), (R_BORE, z_front), (R_BORE, Z_CBACK), (R_SH, Z_CBACK), (R_SH, Z_SHOULDER1),
            (R_SH + 0.5, Z_SHOULDER1), (R_SH + 0.5, Z_SHOULDER2), (R_SH, Z_SHOULDER2), (R_SH, Z_TURB),
            (R_BORE, Z_TURB), (R_BORE, Z_TURB_E + 6.5), (0, Z_TURB_E + 6.5)]


def rect(ri, ro, z0, z1):
    return [(ri, z0), (ro, z0), (ro, z1), (ri, z1)]


SLEEVE_FRONT = rect(R_SH, 6.0, Z_CBACK, Z_BRG1)
SLEEVE_REAR = rect(R_SH, 6.0, Z_BRG2_E, Z_TURB)
WAVE_SPRING = rect(R_BRG - 2.5, R_BRG - 0.1, Z_SHOULDER2 - 1.0, Z_SHOULDER2 - 0.3)


def combustor_outer_profile():
    t = p["liner_t"]
    return [(R_LO - t, Z_COMB_F), (R_LO, Z_COMB_F), (R_LO, Z_OCONE), (R_NGV_T + 1.7, Z_NGV_F),
            (R_NGV_T + 1.7, Z_NGV_F + 4), (R_NGV_T + 1.2, Z_NGV_F + 4), (R_NGV_T + 1.2, Z_NGV_F), (R_LO - t, Z_OCONE)]


def combustor_inner_profile():
    t, r_seat = p["liner_t"], 21.3
    z_ic = Z_OCONE - 5
    return [(R_LI, Z_COMB_F), (R_LI + t, Z_COMB_F), (R_LI + t, z_ic), (r_seat + t, Z_TUN_E), (r_seat + t, Z_NGV_F),
            (r_seat, Z_NGV_F), (r_seat, Z_TUN_E), (R_LI, z_ic)]


COMB_PLATE = rect(R_LI, R_LO, Z_COMB_F - 1.0, Z_COMB_F)
STICK_Z0 = Z_COMB_F - 3


def ngv_hub_profile():
    return [(7.0, Z_TUN_E), (21.25, Z_TUN_E), (21.25, Z_NGV_F), (R_NGV_H, Z_NGV_F + 2), (R_NGV_H, Z_NGV_E),
            (R_NGV_H - 1.5, Z_NGV_E), (R_NGV_H - 1.5, Z_NGV_F + 2), (19.8, Z_TUN_E + 3), (7.0, Z_TUN_E + 3)]


def ngv_ring_profile():
    return [(R_NGV_T, Z_NGV_F), (R_NGV_T + 1.2, Z_NGV_F), (R_NGV_T + 1.2, Z_NGV_E), (R_FL, Z_NGV_E),
            (R_FL, Z_NGV_E + NGV_FLANGE_T), (R_NGV_T, Z_NGV_E + NGV_FLANGE_T)]


def turbine_disk_profile():
    rh = p["turb_hub_d"] / 2
    return [(R_BORE, Z_TURB), (rh, Z_TURB + 0.5), (rh, Z_TURB + p["turb_width"] + 1.5), (10.0, Z_TURB_E),
            (R_BORE, Z_TURB_E)]


CASING_TUBE = rect(R_CASI, R_CAS, Z_CEX_F, Z_NGV_E)
CASING_FRONT_FLANGE = rect(R_CAS - 0.01, R_FL, Z_CEX_F, Z_CEX_F + 3)
CASING_REAR_FLANGE = rect(R_CAS - 0.01, R_FL, Z_NGV_E - 3, Z_NGV_E)


def nozzle_profile():
    t = NOZ_T
    r_exit = p["nozzle_exit_d"] / 2
    z0, z1 = Z_NOZ_F, Z_NOZ_F + NOZ_FLANGE_T
    return [(R_TSH, z0), (R_FL, z0), (R_FL, z1), (R_TSH + t, z1), (R_TSH + t, Z_TURB_E + 1),
            (R_TSH + 1.0 + t, Z_TURB_E + 5), (r_exit + t, NOZ_EXIT_Z), (r_exit, NOZ_EXIT_Z), (R_TSH + 1.0, Z_TURB_E + 5),
            (R_TSH, Z_TURB_E + 1)]


def tail_cone_profile():
    zt = Z_TURB_E
    return [(0, zt + 30), (4.0, zt + 30), (20.5, zt + 2), (9.0, zt + 2), (9.0, zt + 2.8), (19.3, zt + 2.8),
            (3.4, zt + 29.2), (0, zt + 29.2)]


def nozzle_strut():
    return [(12.0, Z_TURB_E + 8), (R_TSH + 1.2, Z_TURB_E + 8), (R_TSH + 1.2, Z_TURB_E + 16), (12.0, Z_TURB_E + 16)]


def starter_arm():
    return [(15.0, Z_STARTER - 10), (18.5, Z_STARTER - 10), (18.5, Z_STARTER), (38.5, -9.0), (38.5, 13.0),
            (34.3, 13.0), (34.3, -8.0), (15.0, Z_STARTER - 4)]


STARTER_HUB = rect(14.2, 17.5, Z_STARTER - 10, Z_STARTER)
STARTER_SCREW_Z = 10.5
COMP_NUT = dict(af=10.0, h=6.0, z0=Z_IND - 6.0, cone_r0=5.5, cone_r1=3.0, cone_h=4.0)
TURB_NUT = dict(af=10.0, h=5.0, z0=Z_TURB_E)


def starter_cone_profile():
    z0 = Z_STARTER + 6
    z_tip1 = COMP_NUT["z0"] - COMP_NUT["cone_h"] - 1.2
    z_tip0 = z_tip1 - 2.2
    return [(1.5, z0), (6.0, z0), (6.0, z_tip0), (4.0, z_tip1), (0.0, z_tip1), (0.0, z0 + 3.0), (1.5, z0 + 3.0)]


STARTER_MOTOR = rect(0.0, 14.0, Z_STARTER - 30, Z_STARTER)


# ---------------------------------------------------------------------------
# Fasteners: (label, diameter, length, head position (x, y, z), shank direction)
# ---------------------------------------------------------------------------
def fasteners():
    out = []
    n = p["n_flange_screws"]
    for i in range(n):
        out.append(("M3x8 intake-casing", 3, 8, polar(R_PCD, 22.5 + i * 360 / n, Z_CEX_F - 4), (0, 0, 1)))
    for s in screw_vanes():
        out.append(("M3x10 intake-diffuser", 3, 10, (s[0], s[1], Z_CEX_F - 4), (0, 0, 1)))
    for i in range(4):
        out.append(("M3x8 tunnel-diffuser", 3, 8, polar(TUNNEL_BOLT_R, 45 + i * 90, Z_BRG1 + 4), (0, 0, -1)))
    for i in range(4):
        out.append(("M3x6 NGV-tunnel", 3, 6, polar(TUNNEL_BOLT_R, 45 + i * 90, Z_TUN_E + 3), (0, 0, -1)))
    for i in range(n):
        out.append(("M3x8 nozzle-casing", 3, 8, polar(R_PCD, 22.5 + i * 360 / n, Z_NOZ_F + NOZ_FLANGE_T), (0, 0, -1)))
    for a in STARTER_ANGLES:
        d = radial_dir(a)
        out.append(("M3x8 starter bracket", 3, 8, polar(38.5, a, STARTER_SCREW_Z), (-d[0], -d[1], 0)))
    for zc in MOUNT_Z:
        out.append(("M3x16 mount clamp", 3, 16, (-8.0, R_CAS + 5.0, zc), (1, 0, 0)))
        out.append(("M3x10 mount-plate", 3, 10, (0.0, Y_PLATE - p["mount_plate_t"], zc), (0, 1, 0)))
    return out
