# SPDX-License-Identifier: LGPL-3.0-or-later
"""Cylinder-based "thick edge" wireframe helpers for pyvoro2 + py3Dmol.

`pyvoro2.viz3d` draws cell/domain wireframes with `view.addLine(...,
lineWidth=...)`, which maps to 3Dmol.js's `addLine`. That, in turn, is
rendered with WebGL's native `gl.LINE_STRIP`, whose width is capped at 1px by
most GPU drivers/browsers (Chrome and most Linux/Windows OpenGL stacks all do
this) — so `VizStyle.edge_line_width` / `domain_line_width` frequently has no
visible effect in the exported HTML, regardless of the value you pass.

The functions here render each wireframe edge as a small capped cylinder
(`view.addCylinder(..., radius=...)`) instead of a line. Cylinder radius is
an actual 3D mesh property, not a rasterization hint, so it renders
consistently thick everywhere. A sphere of the same radius is optionally
added at every vertex touched by a drawn edge, so corners look mitred
instead of leaving a gap/notch where cylinders meet at an angle.

These are drop-in replacements for the *wireframe-only* pieces of
`pyvoro2.viz3d.view_tessellation`. They intentionally do not attempt to
replicate `view_tessellation`'s `wrap_cells`/periodic-image handling; for a
`pyvoro2.Box` domain (the common non-periodic case) that step is a no-op
anyway.

Usage
-----

```python
import pyvoro2 as pv
from pyvoro2.viz3d import make_view, add_sites, add_axes
from thick_edges import add_domain_wireframe_thick, add_tessellation_wireframe_thick

box = pv.Box(((0, 1), (0, 1), (0, 1)))
result = pv.compute(centers, domain=box, mode="power", weights=radii**2)

v = make_view(width=640, height=480)
add_domain_wireframe_thick(v, box, radius=0.004)
add_tessellation_wireframe_thick(v, result.cells, radius=0.01)
v.zoomTo()
v.write_html("power_tessellation_thick.html")
```
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from pyvoro2.domains import Box, OrthorhombicCell, PeriodicCell


def _xyz(p: Sequence[float]) -> dict[str, float]:
    return {"x": float(p[0]), "y": float(p[1]), "z": float(p[2])}


def add_cylinder_edge(
    view: Any,
    start: Sequence[float],
    end: Sequence[float],
    *,
    radius: float = 0.02,
    color: str = "0x1f77b4",
) -> Any:
    """Draw a single edge as a flat-capped cylinder."""

    view.addCylinder(
        {
            "start": _xyz(start),
            "end": _xyz(end),
            "radius": float(radius),
            "color": color,
            "fromCap": 1,
            "toCap": 1,
        }
    )
    return view


def add_cell_wireframe_thick(
    view: Any,
    cell: dict[str, Any],
    *,
    color: str = "0x1f77b4",
    radius: float = 0.02,
    joints: bool = True,
) -> Any:
    """Cylinder version of `pyvoro2.viz3d.add_cell_wireframe`."""

    verts = cell.get("vertices")
    faces = cell.get("faces")
    if verts is None or faces is None:
        return view
    if len(faces) == 0:
        return view
    v = np.asarray(verts, dtype=float)
    if v.ndim != 2 or v.shape[1] != 3 or v.size == 0:
        return view

    edges: set[tuple[int, int]] = set()
    for f in faces:
        idx = f.get("vertices")
        if idx is None or len(idx) == 0:
            continue
        m = len(idx)
        for k in range(m):
            a = int(idx[k])
            b = int(idx[(k + 1) % m])
            if a == b:
                continue
            if a > b:
                a, b = b, a
            edges.add((a, b))

    touched: set[int] = set()
    for a, b in edges:
        if a < 0 or b < 0 or a >= len(v) or b >= len(v):
            continue
        add_cylinder_edge(view, v[a], v[b], radius=radius, color=color)
        touched.add(a)
        touched.add(b)

    if joints:
        for i in touched:
            view.addSphere(
                {"center": _xyz(v[i]), "radius": float(radius), "color": color}
            )
    return view


def add_tessellation_wireframe_thick(
    view: Any,
    cells: Iterable[dict[str, Any]],
    *,
    color: str = "0x1f77b4",
    radius: float = 0.02,
    cell_ids: set[int] | None = None,
    joints: bool = True,
) -> Any:
    """Cylinder version of `pyvoro2.viz3d.add_tessellation_wireframe`."""

    for c in cells:
        cid = c.get("id")
        if cell_ids is not None and cid not in cell_ids:
            continue
        add_cell_wireframe_thick(view, c, color=color, radius=radius, joints=joints)
    return view


def add_domain_wireframe_thick(
    view: Any,
    domain: "Box | OrthorhombicCell | PeriodicCell",
    *,
    color: str = "0x000000",
    radius: float = 0.01,
    joints: bool = True,
) -> Any:
    """Cylinder version of `pyvoro2.viz3d.add_domain_wireframe`."""

    if isinstance(domain, (Box, OrthorhombicCell)):
        (xmin, xmax), (ymin, ymax), (zmin, zmax) = domain.bounds
        o = np.array([xmin, ymin, zmin], dtype=float)
        a = np.array([xmax - xmin, 0.0, 0.0])
        b = np.array([0.0, ymax - ymin, 0.0])
        c = np.array([0.0, 0.0, zmax - zmin])
    elif isinstance(domain, PeriodicCell):
        o = np.array(domain.origin, dtype=float)
        a, b, c = (np.array(vv, dtype=float) for vv in domain.vectors)
    else:  # pragma: no cover
        raise TypeError(f"Unsupported domain type: {type(domain)!r}")

    corners = [
        o,
        o + a,
        o + b,
        o + c,
        o + a + b,
        o + a + c,
        o + b + c,
        o + a + b + c,
    ]
    edges = [
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 4),
        (1, 5),
        (2, 4),
        (2, 6),
        (3, 5),
        (3, 6),
        (4, 7),
        (5, 7),
        (6, 7),
    ]

    touched: set[int] = set()
    for i, j in edges:
        add_cylinder_edge(view, corners[i], corners[j], radius=radius, color=color)
        touched.add(i)
        touched.add(j)

    if joints:
        for i in touched:
            view.addSphere(
                {"center": _xyz(corners[i]), "radius": float(radius), "color": color}
            )
    return view
