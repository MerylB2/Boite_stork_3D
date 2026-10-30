"""Charnière arrière + loquets avant pour les boîtes Stork (inspiré des boîtes « Arduino »).

Repère : boîte posée, face avant en y = 0, face arrière en y = D, joint boîte/couvercle en z = H.
Visserie : charnières = vis M3 x 35 + écrou (ou tige Ø3 mm de 31 mm),
           loquets   = vis M3 x 30 + écrou.
"""
import numpy as np
from manifold3d import Manifold, CrossSection, FillRule, OpType

SEG = 48
# --- charnière (arrière)
CH_R = 4.5          # rayon des charnons
CH_DY = 5.5         # axe à 5,5 mm derrière la face arrière
CH_DZ = -2.1        # axe 2,1 mm sous le joint : le haut des charnons affleure le dessus du couvercle
CH_L = 10.0         # longueur d'un charnon
CH_JEU = 0.4        # jeu entre charnons
TROU = 1.7          # rayon de passage M3 (Ø3,4)
ARRIERE_SANS_JUPE = 7.0   # la jupe du couvercle s'arrête 7 mm avant l'arrière
ARRIERE_MUR_PLEIN = 5.5   # le rebord de la boîte est plein sur les 5,5 derniers mm (dégagement 1,5 mm)
# --- loquets (avant)
LQ_L = 14.0         # largeur d'un loquet
LQ_JEU = 0.4
OREILLE = 4.0       # épaisseur des oreilles de la boîte
AX_Y = -4.0         # axe du loquet, 4 mm devant la face avant
AX_DZ = -10.0       # 10 mm sous le joint
AX_R = 3.4
ERGOT_Z = 0.6       # dessus de l'ergot du couvercle, au-dessus du joint
SERRAGE = 0.3       # recouvrement bec / ergot (encliquetage)


def cyl_x(x0, L, y, z, r):
    return Manifold.cylinder(L, r, r, SEG).rotate([0, 90, 0]).translate([x0, y, z])


def boite_xyz(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def prisme_x(profil_yz, x0, L):
    """Prisme d'axe X à partir d'un profil [(y, z), ...]."""
    cs = CrossSection([profil_yz], FillRule.NonZero)
    m = cs.extrude(L)                                     # (u=y, v=z, w=x)
    return m.transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


def positions(W):
    return [0.2 * W, 0.8 * W]


def groupe_charniere(xc):
    """Abscisses des 3 charnons d'un groupe : boîte / couvercle / boîte."""
    tot = 3 * CH_L + 2 * CH_JEU
    x0 = xc - tot / 2
    return [(x0, "b"), (x0 + CH_L + CH_JEU, "c"), (x0 + 2 * (CH_L + CH_JEU), "b")], (x0, tot)


def ajouts_boite(W, D, H):
    """Charnons côté boîte (arrière) et oreilles des loquets (avant)."""
    yc, zc = D + CH_DY, H + CH_DZ
    plus, trous = [], []
    for xc in positions(W):
        segs, (x0, tot) = groupe_charniere(xc)
        for xs, qui in segs:
            if qui != "b":
                continue
            cyl = cyl_x(xs, CH_L, yc, zc, CH_R)
            demi = cyl ^ boite_xyz(xs - 1, xs + CH_L + 1, D - 2, D + 20, zc - 20, zc)
            bande = boite_xyz(xs, xs + CH_L, D - 1.0, D, H - 15.0, zc)
            plus.append(cyl + Manifold.batch_hull([demi, bande]))
        trous.append(cyl_x(x0 - 1, tot + 2, yc, zc, TROU))
        # oreilles des loquets
        za = H + AX_DZ
        for s in (-1, 1):
            xa = xc + s * (LQ_L / 2 + LQ_JEU) + (0 if s > 0 else -OREILLE)
            c = cyl_x(xa, OREILLE, AX_Y, za, AX_R)
            bande = boite_xyz(xa, xa + OREILLE, -0.2, 0.8, za - AX_R - 7.0, za + AX_R)
            plus.append(Manifold.batch_hull([c, bande]))
        trous.append(cyl_x(xc - LQ_L / 2 - LQ_JEU - OREILLE - 1, LQ_L + 2 * (LQ_JEU + OREILLE) + 2,
                           AX_Y, za, TROU))
    return Manifold.batch_boolean(plus, OpType.Add), Manifold.batch_boolean(trous, OpType.Add)


def ajouts_couvercle(W, D, H, ep):
    """Charnons côté couvercle (arrière) et ergots des loquets (avant). ep = épaisseur du dessus."""
    yc, zc = D + CH_DY, H + CH_DZ
    plus, trous = [], []
    for xc in positions(W):
        segs, (x0, tot) = groupe_charniere(xc)
        for xs, qui in segs:
            if qui != "c":
                continue
            cyl = cyl_x(xs, CH_L, yc, zc, CH_R)
            semelle = boite_xyz(xs, xs + CH_L, D - 3.0, yc + CH_R, H, H + ep)
            plus.append(cyl + semelle)
        trous.append(cyl_x(x0 - 1, tot + 2, yc, zc, TROU))
        # ergot sur la face avant du couvercle
        zr = H + ERGOT_Z
        prof = [(0.4, zr), (-2.0, zr), (-2.0, zr - 1.2), (0.4, zr - 3.6)]
        plus.append(prisme_x(prof, xc - LQ_L / 2, LQ_L))
    return Manifold.batch_boolean(plus, OpType.Add), Manifold.batch_boolean(trous, OpType.Add)


def coupe_jupe_arriere(W, D, H):
    """Volume à retirer du couvercle : jupe arrière (la charnière assure le centrage)."""
    return boite_xyz(-5, W + 5, D - ARRIERE_SANS_JUPE, D + 30, H - 20, H)


def coupe_rebord_arriere(W, D, H):
    """Zone où le rebord de la boîte n'est PAS creusé (mur plein jusqu'au joint, à l'arrière)."""
    return boite_xyz(-5, W + 5, D - ARRIERE_MUR_PLEIN, D + 5, H - 20, H + 5)


def loquet(H=0.0):
    """Loquet, en place (même repère que la boîte, centré en x = 0)."""
    za = H + AX_DZ
    zr = H + ERGOT_Z
    z_haut = H + 4.4
    lb = zr - SERRAGE
    bras = [(-5.0, za), (-2.6, za), (-2.6, z_haut), (-5.0, z_haut)]
    bec = [(-2.6, lb), (-1.4, lb), (-0.6, lb + 0.8), (-0.6, z_haut), (-2.6, z_haut)]
    m = prisme_x(bras, -LQ_L / 2, LQ_L) + prisme_x(bec, -LQ_L / 2, LQ_L)
    m = m + cyl_x(-LQ_L / 2, LQ_L, AX_Y, za, AX_R)
    m = m - cyl_x(-LQ_L / 2 - 1, LQ_L + 2, AX_Y, za, TROU)
    return m


def loquet_impression():
    """Loquet couché sur son profil (axe de la vis vertical), posé sur le plateau."""
    m = loquet(0.0).rotate([0, -90, 0])
    b = m.bounding_box()
    return m.translate([-b[0], -b[1], -b[2]])
