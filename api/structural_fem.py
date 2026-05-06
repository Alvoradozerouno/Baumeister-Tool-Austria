"""
ORION Architekt-AT — FEM Tragwerksberechnung
=============================================
Euler-Bernoulli Balken-FEM nach Eurocode mit scipy/numpy.
Supports: Einfeldträger, Durchlaufträger, einfacher Rahmen.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.linalg import solve  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _ek_check(max_deflection_mm: float, length_m: float) -> Dict:
    """Eurocode SLS deflection check: δ ≤ L/250."""
    limit_mm = length_m * 1000 / 250
    return {
        "deflection_ok": max_deflection_mm <= limit_mm,
        "limit_mm": round(limit_mm, 2),
        "actual_mm": round(max_deflection_mm, 2),
        "criterion": "L/250 (Eurocode EN 1990)",
    }


# ---------------------------------------------------------------------------
# Single-span beam (Einfeldträger)
# ---------------------------------------------------------------------------

def solve_single_span_beam(
    length_m: float,
    E_GPa: float,
    I_cm4: float,
    q_kN_m: float,
    F_kN: float = 0.0,
    F_pos_m: float = 0.0,
    support_left: str = "pinned",
    support_right: str = "pinned",
    n_elements: int = 40,
) -> Dict:
    """
    Euler-Bernoulli Balken FEM.

    DOFs per node: [w, φ]  (vertical displacement, rotation)
    Element: 2-node Hermitian beam element (4 DOFs)
    """
    E = E_GPa * 1e9          # Pa
    I = I_cm4 * 1e-8          # m⁴
    EI = E * I

    n_nodes = n_elements + 1
    n_dof = 2 * n_nodes       # [w0, φ0, w1, φ1, ...]
    L_e = length_m / n_elements

    # Global stiffness matrix
    K = np.zeros((n_dof, n_dof))
    F_vec = np.zeros(n_dof)

    def _k_local(Le: float) -> np.ndarray:
        """Local stiffness matrix for Euler-Bernoulli beam element."""
        c = EI / Le ** 3
        return c * np.array([
            [ 12,  6*Le,  -12,  6*Le],
            [ 6*Le, 4*Le**2, -6*Le, 2*Le**2],
            [-12, -6*Le,   12, -6*Le],
            [ 6*Le, 2*Le**2, -6*Le, 4*Le**2],
        ])

    # Assemble global K
    for e in range(n_elements):
        dofs = [2*e, 2*e+1, 2*e+2, 2*e+3]
        Ke = _k_local(L_e)
        for i, di in enumerate(dofs):
            for j, dj in enumerate(dofs):
                K[di, dj] += Ke[i, j]

    # Distributed load q (kN/m → N/m)
    q_N_m = q_kN_m * 1000
    for e in range(n_elements):
        dofs = [2*e, 2*e+1, 2*e+2, 2*e+3]
        fe = q_N_m * L_e / 2 * np.array([1, L_e/6, 1, -L_e/6])
        for i, di in enumerate(dofs):
            F_vec[di] += fe[i]

    # Concentrated load F
    if abs(F_kN) > 1e-9:
        F_N = F_kN * 1000
        node_idx = min(int(F_pos_m / L_e + 0.5), n_nodes - 1)
        F_vec[2 * node_idx] += F_N

    # Boundary conditions
    constrained: List[int] = []
    if support_left in ("pinned", "fixed", "roller"):
        constrained.append(0)     # w=0
    if support_left == "fixed":
        constrained.append(1)     # φ=0
    if support_right in ("pinned", "fixed"):
        constrained.append(2 * (n_nodes - 1))
    if support_right == "fixed":
        constrained.append(2 * (n_nodes - 1) + 1)

    free = [i for i in range(n_dof) if i not in constrained]

    Kff = K[np.ix_(free, free)]
    Ff = F_vec[free]

    u_free = solve(Kff, Ff)
    u = np.zeros(n_dof)
    for i, f in enumerate(free):
        u[f] = u_free[i]

    # Extract deflections and compute moments/shears
    w = u[0::2]   # vertical displacements (m)
    x_vals = np.linspace(0, length_m, n_nodes)

    # Bending moment at each node (M = EI * d²w/dx²)
    M = np.zeros(n_nodes)
    V = np.zeros(n_nodes)
    for e in range(n_elements):
        dofs = [2*e, 2*e+1, 2*e+2, 2*e+3]
        u_e = u[dofs]
        # Curvature at midpoint
        kappa = (u_e[2] - 2 * u_e[0] + u_e[0]) / L_e ** 2  # approx
        M[e] += EI * (6 / L_e ** 2) * (u_e[0] - u_e[2]) + EI * (4 / L_e) * u_e[1] + EI * (2 / L_e) * u_e[3]
        V[e] = EI * 12 / L_e ** 3 * (u_e[0] - u_e[2]) + EI * 6 / L_e ** 2 * (u_e[1] + u_e[3])

    # Exact analytical solutions for validation/override (simply supported + UDL)
    if support_left == "pinned" and support_right == "pinned" and abs(F_kN) < 1e-9:
        L = length_m
        # M(x) = q*L*x/2 - q*x²/2
        xp = np.linspace(0, L, 200)
        M_exact = (q_kN_m * L * xp / 2 - q_kN_m * xp ** 2 / 2)  # kNm
        V_exact = q_kN_m * L / 2 - q_kN_m * xp              # kN
        w_exact = (q_kN_m * 1000 / (24 * EI)) * xp * (L ** 3 - 2 * L * xp ** 2 + xp ** 3)  # m
        max_moment = float(np.max(np.abs(M_exact)))
        max_shear = float(np.max(np.abs(V_exact)))
        max_deflection_m = float(np.max(np.abs(w_exact)))
        R_left = q_kN_m * L / 2
        R_right = q_kN_m * L / 2
        moment_diagram = [[round(float(x), 3), round(float(m), 3)] for x, m in zip(xp, M_exact)]
    else:
        # Use FEM results
        max_moment = float(np.max(np.abs(M))) / 1000  # → kNm
        max_shear = float(np.max(np.abs(V))) / 1000   # → kN
        max_deflection_m = float(np.max(np.abs(w)))
        R_left = float(F_vec[0] - np.dot(K[0, free], u_free)) / 1000
        R_right = float(F_vec[-2] - np.dot(K[-2, free], u_free)) / 1000
        moment_diagram = [[round(float(x), 3), round(float(m)/1000, 3)] for x, m in zip(x_vals, M)]

    max_deflection_mm = max_deflection_m * 1000

    return {
        "max_moment_kNm": round(max_moment, 2),
        "max_shear_kN": round(abs(max_shear), 2),
        "max_deflection_mm": round(max_deflection_mm, 2),
        "reactions": {"R_links_kN": round(R_left, 2), "R_rechts_kN": round(R_right, 2)},
        "eurocode_check": _ek_check(max_deflection_mm, length_m),
        "moment_diagram": moment_diagram,
        "parameters": {
            "L_m": length_m, "E_GPa": E_GPa, "I_cm4": I_cm4,
            "q_kN_m": q_kN_m, "F_kN": F_kN,
        },
    }


# ---------------------------------------------------------------------------
# Continuous beam (Durchlaufträger)
# ---------------------------------------------------------------------------

def solve_continuous_beam(
    spans_m: List[float],
    E_GPa: float,
    I_cm4: float,
    q_kN_m: List[float],
    n_elements_per_span: int = 20,
) -> Dict:
    """
    Continuous beam over multiple spans using three-moment equation (Clapeyron).
    All spans simply supported at outer edges, interior supports are pinned.
    """
    n = len(spans_m)
    if len(q_kN_m) != n:
        q_kN_m = [q_kN_m[0]] * n

    EI = E_GPa * 1e9 * I_cm4 * 1e-8

    # Three-moment equation (Clapeyron's theorem)
    # M_0 = M_n = 0 (outer supports)
    # 6*EI * (moment terms) = fixed-end moments from UDL
    if n == 1:
        return solve_single_span_beam(spans_m[0], E_GPa, I_cm4, q_kN_m[0])

    # For 2-span case: solve for M_1 at interior support
    if n == 2:
        L1, L2 = spans_m
        q1, q2 = q_kN_m
        # Clapeyron: L1*M0 + 2*(L1+L2)*M1 + L2*M2 = -6*(q1*L1³/4 + q2*L2³/4)/EI * EI
        # M0=M2=0:
        M1 = -(q1 * L1 ** 3 / 4 + q2 * L2 ** 3 / 4) / (2 * (L1 + L2))
        # Reactions
        R0 = q1 * L1 / 2 + M1 / L1
        R1_left = q1 * L1 / 2 - M1 / L1
        R1_right = q2 * L2 / 2 - M1 / L2
        R2 = q2 * L2 / 2 + M1 / L2

        # Moment diagrams per span
        x1 = np.linspace(0, L1, 100)
        M1_diag = R0 * x1 - q1 * x1 ** 2 / 2
        x2 = np.linspace(0, L2, 100)
        M2_diag = R1_right * x2 - q2 * x2 ** 2 / 2

        # Max values
        Mmax1 = float(np.max(np.abs(M1_diag)))
        Mmax2 = float(np.max(np.abs(M2_diag)))
        max_moment = max(Mmax1, Mmax2, abs(M1))

        # Deflection (approx)
        def_1 = 5 * q1 * 1000 * L1 ** 4 / (384 * EI) * 1000
        def_2 = 5 * q2 * 1000 * L2 ** 4 / (384 * EI) * 1000

        moment_diagram = (
            [[round(float(x), 3), round(float(m), 3)] for x, m in zip(x1, M1_diag)]
            + [[round(float(x + L1), 3), round(float(m), 3)] for x, m in zip(x2, M2_diag)]
        )

        return {
            "max_moment_kNm": round(max_moment, 2),
            "moment_interior_support_kNm": round(float(M1), 2),
            "max_shear_kN": round(max(R0, R1_left, R1_right, R2), 2),
            "max_deflection_mm": round(max(def_1, def_2), 2),
            "reactions": {
                "R_links_kN": round(R0, 2),
                "R_mitte_links_kN": round(R1_left, 2),
                "R_mitte_rechts_kN": round(R1_right, 2),
                "R_rechts_kN": round(R2, 2),
            },
            "eurocode_check": _ek_check(max(def_1, def_2), max(spans_m)),
            "moment_diagram": moment_diagram,
        }

    # General n-span: build tridiagonal system
    A = np.zeros((n - 1, n - 1))
    b_vec = np.zeros(n - 1)
    for i in range(n - 1):
        if i > 0:
            A[i, i - 1] = spans_m[i]
        A[i, i] = 2 * (spans_m[i] + spans_m[i + 1])
        if i < n - 2:
            A[i, i + 1] = spans_m[i + 1]
        b_vec[i] = -(q_kN_m[i] * spans_m[i] ** 3 / 4 + q_kN_m[i + 1] * spans_m[i + 1] ** 3 / 4)

    M_interior = np.linalg.solve(A, b_vec)
    max_m = float(np.max(np.abs(M_interior)))
    max_defl = 5 * max(q_kN_m) * 1000 * max(spans_m) ** 4 / (384 * EI) * 1000

    return {
        "max_moment_kNm": round(max_m, 2),
        "max_shear_kN": round(max(q_kN_m) * max(spans_m) / 2, 2),
        "max_deflection_mm": round(max_defl, 2),
        "reactions": {"hinweis": "Auflagerkräfte für n>2 Felder: Reaktionskräfte aus Momentengleichgewicht"},
        "eurocode_check": _ek_check(max_defl, max(spans_m)),
        "moment_diagram": [],
    }


# ---------------------------------------------------------------------------
# Simple frame (Einfacher Rahmen)
# ---------------------------------------------------------------------------

def solve_simple_frame(
    width_m: float,
    height_m: float,
    horizontal_load_kN: float,
    vertical_load_kN_m: float,
    E_GPa: float = 30.0,
    I_col_cm4: float = 5000.0,
    I_beam_cm4: float = 8000.0,
) -> Dict:
    """
    Portal frame: two columns (pinned at base) + one beam.
    Horizontal load applied at top of left column.
    Vertical UDL on beam.
    """
    EI_col = E_GPa * 1e9 * I_col_cm4 * 1e-8
    EI_beam = E_GPa * 1e9 * I_beam_cm4 * 1e-8
    L = width_m
    H = height_m
    F_h = horizontal_load_kN  # kN
    q_v = vertical_load_kN_m  # kN/m

    # Stiffness coefficients for portal frame (sway method)
    # Column stiffness (pinned base): 3EI/H³
    k_col = 3 * EI_col / H ** 3  # N/m
    # Two columns in parallel
    K_total = 2 * k_col  # N/m

    # Horizontal sway displacement Δ
    F_h_N = F_h * 1000
    delta_m = F_h_N / K_total  # m

    # Column moments (at top)
    M_col_Nm = 3 * EI_col / H ** 2 * delta_m  # N·m
    M_col_kNm = M_col_Nm / 1000

    # Beam moments from vertical load (fixed-fixed approximation for frame)
    M_beam_end = q_v * L ** 2 / 12   # kNm (fixed-end moment)
    M_beam_mid = q_v * L ** 2 / 24   # kNm

    # Vertical reactions
    R_v = q_v * L / 2  # kN (symmetric)
    R_h = F_h / 2       # kN (each column)

    # Max deflection (beam + sway)
    defl_sway_mm = delta_m * 1000
    defl_beam_mm = q_v * 1000 * L ** 4 / (384 * EI_beam) * 1000
    max_defl_mm = max(defl_sway_mm, defl_beam_mm)

    # Drift check: Δ ≤ H/300 (Eurocode)
    drift_limit_mm = H * 1000 / 300
    drift_ok = defl_sway_mm <= drift_limit_mm

    return {
        "max_moment_kNm": round(max(M_col_kNm, M_beam_end), 2),
        "column_moment_top_kNm": round(M_col_kNm, 2),
        "beam_end_moment_kNm": round(M_beam_end, 2),
        "beam_mid_moment_kNm": round(M_beam_mid, 2),
        "max_shear_kN": round(max(R_h, q_v * L / 2), 2),
        "max_deflection_mm": round(max_defl_mm, 2),
        "horizontal_sway_mm": round(defl_sway_mm, 2),
        "reactions": {
            "R_vertikal_kN": round(R_v, 2),
            "R_horizontal_kN": round(R_h, 2),
        },
        "eurocode_check": {
            "deflection_ok": drift_ok,
            "limit_mm": round(drift_limit_mm, 1),
            "actual_mm": round(defl_sway_mm, 2),
            "criterion": "H/300 (Eurocode EN 1990, Rahmen-Drift)",
        },
        "parameters": {"B": width_m, "H": height_m, "F_h": F_h, "q_v": q_v},
    }
