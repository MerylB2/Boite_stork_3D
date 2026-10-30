"""Logo 42 AERO PARIS (vectorisé depuis assets/logo_42_aero_paris.png) et silhouette de quadplane."""
import os
import numpy as np
from PIL import Image
from skimage import measure
from manifold3d import CrossSection, FillRule, JoinType

ICI = os.path.dirname(os.path.abspath(__file__))
_LOGO = None


def _rr(w, d, r, cx=0.0, cy=0.0):
    r = max(0.01, min(r, w / 2 - 0.01, d / 2 - 0.01))
    return CrossSection.square([w - 2 * r, d - 2 * r]).translate(
        [cx - w / 2 + r, cy - d / 2 + r]).offset(r, JoinType.Round)


def _centrer_echelle(cs, hauteur=None, largeur=None):
    x0, y0, x1, y1 = cs.bounds()
    s = min(hauteur / (y1 - y0) if hauteur else 1e9, largeur / (x1 - x0) if largeur else 1e9)
    return cs.translate([-(x0 + x1) / 2, -(y0 + y1) / 2]).scale([s, s])


def logo_cs(hauteur=None, largeur=None):
    """Formes noires du logo, centrées en (0, 0), à la taille demandée (mm)."""
    global _LOGO
    if _LOGO is None:
        im = Image.open(os.path.join(ICI, "assets", "logo_42_aero_paris.png")).convert("L")
        k = 4
        im = im.resize((im.width * k, im.height * k), Image.BICUBIC)
        a = np.asarray(im).astype(float)
        a = np.pad(a, 2, constant_values=255)
        contours = measure.find_contours(a, 110)
        polys = []
        for c in contours:
            c = measure.approximate_polygon(c, tolerance=0.8)
            if len(c) < 4:
                continue
            polys.append([(x / k, -y / k) for y, x in c[:-1]])
        _LOGO = CrossSection(polys, FillRule.EvenOdd)
    return _centrer_echelle(_LOGO, hauteur, largeur)


def drone_cs(hauteur=None, largeur=None):
    """Quadplane vu de dessus, nez vers la droite : fuselage, aile, 2 poutres,
    4 rotors de sustentation, empennage en V et hélice propulsive."""
    parts = []
    parts.append(_rr(62, 7, 3.5, cx=2, cy=0))                                   # fuselage
    parts.append(CrossSection([[(30, 3), (36, 3), (40, 0), (36, -3), (30, -3)]], FillRule.NonZero))  # nez effilé
    aile = CrossSection([[(4, 34), (12, 34), (14, 3), (14, -3), (12, -34), (4, -34), (0, -3), (0, 3)]], FillRule.NonZero)
    parts.append(aile)
    for y in (16, -16):
        parts.append(_rr(48, 2.6, 1.3, cx=6, cy=y))                             # poutres
        for x in (-17, 29):
            ext = CrossSection.circle(11.0, 64).translate([x, y])
            anneau = ext - CrossSection.circle(9.4, 64).translate([x, y])       # disque d'hélice
            parts.append(anneau)
            parts.append(CrossSection.circle(2.6, 32).translate([x, y]))        # moteur
            parts.append(_rr(20, 1.4, 0.7).rotate(35).translate([x, y]))       # pales
    vtail = CrossSection([[(-28, 2), (-24, 2), (-30, 13), (-34, 13)]], FillRule.NonZero)
    parts.append(vtail)
    parts.append(vtail.mirror([0, 1]))
    parts.append(_rr(2.0, 16, 1.0, cx=-31, cy=0))                               # hélice propulsive
    cs = parts[0]
    for p in parts[1:]:
        cs = cs + p
    return _centrer_echelle(cs, hauteur, largeur)
