#!/usr/bin/env python3
"""
Boîtes de rangement compartimentées – Prototype n°1 Stork VTOL (Flightory)
Équipe « No GPS, No Panic » – UAV Challenge

Génère, pour chaque boîte : la boîte (STL) + son couvercle (STL, déjà retourné
pour l'impression). Tout est paramétrique : modifiez les dimensions des
compartiments dans BOITES puis relancez :

    pip install manifold3d trimesh matplotlib numpy
    python3 generer_boites.py

Principe des dimensions (en mm) :
  - les compartiments sont décrits en rangées (axe Y, de l'avant vers l'arrière),
    chaque rangée contient des cases (axe X, de gauche à droite) ;
  - une largeur ou une profondeur "*" prend toute la place restante ;
  - ce sont des dimensions INTÉRIEURES de case (marge déjà incluse autour de la pièce).
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection, JoinType, FillRule, OpType, set_circular_segments
import zipfile
import decor
import fermeture
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

set_circular_segments(48)

# ---------------------------------------------------------------- paramètres
MUR_EXT = 3.0        # épaisseur paroi extérieure
CLOISON = 1.2        # épaisseur des cloisons (3 lignes en buse 0,4)
FOND = 2.0           # épaisseur du fond
R_EXT = 5.0          # rayon des angles extérieurs
R_CASE = 1.5         # rayon des angles des cases
REBORD_H = 6.0       # hauteur du rebord qui reçoit le couvercle
REBORD_RETRAIT = 1.5 # retrait du rebord (épaisseur de la jupe du couvercle + jeu)
JEU = 0.2            # jeu par côté entre rebord et jupe (0,15 serré / 0,3 libre)
COUV_EP = 2.4        # épaisseur du dessus du couvercle
GRAVURE = 0.6        # profondeur des textes gravés
FONT = FontProperties(family="DejaVu Sans", weight="bold")
TAILLES = []          # hauteurs de texte utilisées (contrôle)
ASSEMBLAGE = {}       # boîte + couvercle en position fermée (contrôles)

# Boîtes imprimées sur la Bambu X1C en 3 couleurs (AMS) ; les autres restent en STL
BAMBU = ["1_electronique", "2_moteurs_servos", "3_pack_vtol_petg", "4_quincaillerie",
         "5_helices", "6_kit_base_petg", "7_kit_base_lwpla"]   # toutes les boîtes
# Emplacements AMS : 1 = noir (boîte), 2 = bleu (couvercle), 3 = blanc (textes)
AMS_NOIR, AMS_BLEU, AMS_BLANC = 1, 2, 3

# ------------------------------------------------------------ boîtes du proto
# Dimensions des pièces relevées dans la BOM v1 et les fiches produits ;
# celles marquées (est.) sont estimées : vérifiez au pied à coulisse.
BOITES = [
    {
        "fichier": "1_electronique",
        "titre": "STORK - ELECTRONIQUE",
        "l": 220, "p": 150, "h": 32,
        "rangees": [
            (46, [(62, "LUCID H7\nWING"),            # TBS Lucid H7 Wing, 54 x 36 mm
                  (52, "ESC 4-EN-1\n65A"),           # Hobbywing 65A (est. 45x45)
                  (44, "GPS\nBN-880"),               # 28x28x10 + câble
                  ("*", "FS-iA10B\nx2")]),           # 47x33x15, 2 empilés
            (40, [(70, "ESC PROPU\nF35A / TEKKO"),
                  (60, "LORA\nRFM95W x2"),
                  ("*", "ESP32 PONT\nANTENNES 868")]),
            ("*", [(110, "RALLONGES SERVO\nCABLES"),
                   ("*", "CONDOS\nXT60 BULLETS")]),
        ],
    },
    {
        "fichier": "2_moteurs_servos",
        "titre": "STORK - MOTEURS",
        "l": 202, "p": 118, "h": 40,
        "rangees": [
            (38, [(38, "VTOL 1"), (38, "VTOL 2"), (38, "VTOL 3"), (38, "VTOL 4"),  # 2212 920KV, Ø28
                  ("*", "AVENGER\n2810")]),                                        # Ø34, 65 g
            (36, [(15, "S1"), (15, "S2"), (15, "S3"), (15, "S4"),                  # EMAX ES08MA II 32,5x11,5x24
                  (60, "ADAPT.\nHELICE M5"),
                  ("*", "VIS\nMOTEURS M3")]),
            ("*", [(38, "SPARE\n2212"), (38, "SPARE\n2212"),
                   ("*", "PALONNIERS / TRINGLES")]),
        ],
    },
    {
        # Pack VTOL – pièces rigides PETG/PC. Cotes mesurées sur les STL Flightory
        # (boîte englobante minimale) + 4 à 6 mm de marge. Compactée pour la X1C.
        "fichier": "3_pack_vtol_petg",
        "titre": "STORK - PACK VTOL PETG",
        "l": 244, "p": 214.4, "h": 38,
        "rangees": [
            (84, [("*", "MAIN SKIDS VTOL")]),                          # 239,8 x 80,4 x 34,7
            (86, [(214, "BATTERY PAD VTOL\n+ FIN TIP VTOL"),          # 209,2 x 80,9 x 6 / 68,7 x 20 x 7,3
                  ("*", "BOOM\nMOUNT 1\nx4")]),                       # 30,4 x 10 x 6
            ("*", [(69, "MOTOR MOUNT 1\nVTOL x4"),                    # 63,8 x 36 x 9 (empilés : 36)
                   (110, "BOOM MOUNT\nGUIDE"),                        # 105 x 36 x 10,9
                   (33, "MOTOR\nMOUNT 2\nx4"),                        # 28 x 27,8 x 9 (empilés : 36)
                   ("*", "BOOM\nMOUNT 2\nx4")]),                      # 30,4 x 12 x 10
        ],
    },
    {
        # Kit de base – pièces rigides PETG. Cotes mesurées sur les STL Flightory.
        "fichier": "6_kit_base_petg",
        "titre": "STORK - KIT DE BASE PETG",
        "l": 236, "p": 214, "h": 30,
        "rangees": [
            (27, [("*", "FUS ROOT L + R")]),                            # 222,6 x 21,7 x 7 (x2 empilés)
            (27, [("*", "WING ROOT L + R")]),                           # 222,3 x 21,7 x 7 (x2 empilés)
            (100, [(125, "SERVO COVER L + R\nWING BAY PLATE L + R"),   # 120 x 50 x 10 / 120,4 x 45,6 x 13,3
                   ("*", "FRONT\nREINFORCEMENT")]),                    # 104 x 95 x 8
            ("*", [(55, "MOTOR MOUNT\n19x19"),                         # 50,6 x 49 x 21
                   (24, "WING\nBOLT\nx2"),                             # 46,6 x 10 x 10
                   (30, "KNOB x2\nWASHER\nx4"),                        # 16 x 16 x 15 / Ø17,5
                   (60, "LOCK 1/2/3\nx6"),                             # 54,2 / 37 / 27,2 mm
                   ("*", "DIVERS")]),
        ],
    },
    {
        # Kit de base – pièces LW-PLA plates (rechanges fragiles), empilées par paires ou par 4.
        # Disposition tournée de 90° (« transposer ») : charnière sur le grand côté, 250 x 203 mm.
        "fichier": "7_kit_base_lwpla",
        "titre": "STORK - KIT DE BASE LW-PLA",
        "l": 180, "p": 237.6, "h": 42, "transposer": True,
        "rangees": [
            (89, [("*", "WINGTIP 3 L + R")]),                           # 169,1 x 84,3 x 18 (x2 empilés)
            (61, [(145, "AILERON 1 + 2\nL + R"), ("*", "RECH.")]),      # 139,9 x 55,7 x 9,9 (x4 : 38)
            (50, [(133, "RUDDER 1 + 2\nL + R"), ("*", "RECH.")]),       # 128,2 x 44,8 x 9,2 (x4 : 37)
            ("*", [(135, "V TAIL 3 L + R"), ("*", "RECH.")]),            # 129,8 x 29,2 x 12 (x2 : 24)
        ],
    },
    {
        "fichier": "4_quincaillerie",
        "titre": "STORK - VISSERIE",
        "l": 176, "p": 120, "h": 25,
        "rangees": [
            ("*", [("*", "M3x6"), ("*", "M3x8"), ("*", "M3x10\nM3x12"), ("*", "ECROUS\nM3")]),
            ("*", [("*", "RONDELLES\nM3"), ("*", "INSERTS\nLAITON"), ("*", "BULLETS\n3,5 mm"), ("*", "XT60\nM/F")]),
            ("*", [("*", "FICHES\nSERVO"), ("*", "GAINE\nTHERMO"), ("*", "COLLIERS\nVELCRO"), ("*", "DIVERS")]),
        ],
    },
    {
        "fichier": "5_helices",
        "titre": "STORK - HELICES",
        "l": 244, "p": 134, "h": 28,     # hélice 9,4" = 239 mm -> 244 intérieur
        "rangees": [
            (32, [("*", "DJI 9450 - CW")]),
            (32, [("*", "DJI 9450 - CCW")]),
            (32, [("*", "PROPULSION 9x6 / 9x4,5")]),
            ("*", [("*", "RECHANGES")]),
        ],
    },
]

# -------------------------------------------------------------- géométrie
def rrect(w, d, r):
    r = max(0.01, min(r, w / 2 - 0.01, d / 2 - 0.01))
    return CrossSection.square([w - 2 * r, d - 2 * r]).translate([r, r]).offset(
        r, JoinType.Round)


def resoudre(tailles, total):
    """Remplace les '*' par la place restante (cloisons comprises)."""
    fixes = sum(t for t in tailles if t != "*")
    n_auto = sum(1 for t in tailles if t == "*")
    reste = total - fixes - CLOISON * (len(tailles) - 1)
    if n_auto:
        auto = reste / n_auto
        if auto < 8:
            raise ValueError(f"Case auto trop petite ({auto:.1f} mm)")
        return [auto if t == "*" else t for t in tailles]
    if abs(reste) > 0.05:
        raise ValueError(f"Les cases font {total - reste:.1f} mm pour {total} mm disponibles")
    return list(tailles)


def cases(boite):
    """Liste (x, y, w, d, texte) en coordonnées intérieures."""
    prof = resoudre([r[0] for r in boite["rangees"]], boite["p"])
    out, y = [], 0.0
    for (_, cellules), d in zip(boite["rangees"], prof):
        larg = resoudre([c[0] for c in cellules], boite["l"])
        x = 0.0
        for (_, txt), w in zip(cellules, larg):
            out.append((x, y, w, d, txt))
            x += w + CLOISON
        y += d + CLOISON
    if boite.get("transposer"):
        L = boite["l"]
        out = [(y, L - x - w, d, w, txt) for (x, y, w, d, txt) in out]
    return out


def dims(b):
    """Dimensions intérieures (l, p) une fois la disposition éventuellement tournée."""
    return (b["p"], b["l"]) if b.get("transposer") else (b["l"], b["p"])


def texte_cs(txt, w_max, h_max, taille_max=6.0):
    """Texte multi-lignes centré en (0,0), ajusté pour tenir dans w_max x h_max."""
    lignes = txt.split("\n")
    polys_l, larg_l = [], []
    for li in lignes:
        tp = TextPath((0, 0), li, size=1.0, prop=FONT)
        polys = [p for p in tp.to_polygons() if len(p) >= 3]
        polys_l.append(polys)
        bb = tp.get_extents()
        larg_l.append((bb.x0, bb.x1))
    interligne = 1.25
    larg = max(x1 - x0 for x0, x1 in larg_l)
    haut = 0.75 + interligne * (len(lignes) - 1)
    s = min(taille_max, w_max / larg, h_max / haut)
    contours = []
    for i, (polys, (x0, x1)) in enumerate(zip(polys_l, larg_l)):
        dy = (len(lignes) - 1) / 2 * interligne - i * interligne - 0.36
        dx = -(x0 + x1) / 2
        for p in polys:
            contours.append([((px + dx) * s, (py + dy) * s) for px, py in p])
    return CrossSection(contours, FillRule.EvenOdd), s


def etiquette(txt, w, d, fw, fd, tmax):
    """Nom de case centré en (0,0) ; écrit à la verticale si la case est haute et étroite."""
    cs, t = texte_cs(txt, w * fw, d * fd, tmax)
    if d > 1.6 * w:
        cs2, t2 = texte_cs(txt, d * fw, w * fd, tmax)
        if t2 > t * 1.2:
            return cs2.rotate(90), t2
    return cs, t


def boite_et_couvercle(b):
    l_in, p_in = dims(b)
    W = l_in + 2 * MUR_EXT
    D = p_in + 2 * MUR_EXT
    H = FOND + b["h"]
    liste = cases(b)

    # --- corps
    corps = rrect(W, D, R_EXT).extrude(H)
    anneau = (rrect(W + 2, D + 2, R_EXT + 1).translate([-1, -1]) -
              rrect(W - 2 * REBORD_RETRAIT, D - 2 * REBORD_RETRAIT,
                    R_EXT - REBORD_RETRAIT).translate([REBORD_RETRAIT, REBORD_RETRAIT]))
    corps = corps - (anneau.extrude(REBORD_H + 1).translate([0, 0, H - REBORD_H])
                     - fermeture.coupe_rebord_arriere(W, D, H))
    textes_b = []
    for (x, y, w, d, txt) in liste:
        poche = rrect(w, d, R_CASE).extrude(b["h"] + 1).translate(
            [MUR_EXT + x, MUR_EXT + y, FOND])
        corps = corps - poche
        # étiquette au fond de la case (gravée, ou incrustée en blanc dans le 3MF)
        cs, t = etiquette(txt, w, d, 0.85, 0.6, 5.0)
        TAILLES.append(t)
        textes_b.append(cs.extrude(GRAVURE + 0.01).translate(
            [MUR_EXT + x + w / 2, MUR_EXT + y + d / 2, FOND - GRAVURE]))
    textes_b = Manifold.batch_boolean(textes_b, OpType.Add)
    incrust_b = corps ^ textes_b
    corps = corps - textes_b

    # titre gravé sur la face avant (sous le rebord)
    zone_h = H - REBORD_H - 4
    cs, _ = texte_cs(b["titre"], 0.6 * W - 2 * (fermeture.LQ_L / 2 + fermeture.LQ_JEU + fermeture.OREILLE) - 8,
                     zone_h * 0.7, 9.0)
    plaque = cs.extrude(0.8 + 0.01)                       # texte dans le plan XY
    plaque = plaque.rotate([90, 0, 0])                      # -> plan XZ, normale -Y
    plaque = plaque.translate([W / 2, 0.8, 2 + zone_h / 2])
    corps = corps - plaque

    # --- couvercle (modélisé en place, puis retourné)
    Wi = W - 2 * REBORD_RETRAIT + 2 * JEU
    Di = D - 2 * REBORD_RETRAIT + 2 * JEU
    jupe_h = REBORD_H - 0.4
    # contour du couvercle (les loquets remplacent la languette d'ouverture)
    contour = rrect(W, D, R_EXT)
    couv = contour.extrude(COUV_EP + jupe_h).translate([0, 0, H - jupe_h])
    logement = rrect(Wi, Di, R_EXT - REBORD_RETRAIT + JEU).translate(
        [REBORD_RETRAIT - JEU, REBORD_RETRAIT - JEU]).extrude(jupe_h + 0.01).translate(
        [0, 0, H - jupe_h - 0.01])
    couv = couv - logement - fermeture.coupe_jupe_arriere(W, D, H)
    # FACE INTÉRIEURE : plan des cases (noms + cadres), juste au-dessus de chaque case.
    # Texte en miroir dans le modèle pour se lire en regardant l'intérieur du couvercle.
    z_int = H                                     # dessous de la plaque du couvercle
    z_ext = H + COUV_EP - GRAVURE                 # dessus du couvercle

    def extr(cs, z):
        return cs.extrude(GRAVURE + 0.01).translate([0, 0, z - (0.01 if z == z_int else 0)])

    blancs, noirs = [], []
    for (x, y, w, d, txt) in liste:
        cs, t = etiquette(txt, w, d, 0.8, 0.55, 5.0)
        TAILLES.append(t)
        cs = cs.mirror([0, 1])
        blancs.append(extr(cs.translate([MUR_EXT + x + w / 2, MUR_EXT + y + d / 2]), z_int))
        cadre = (rrect(w - 2, d - 2, R_CASE) - rrect(w - 3.6, d - 3.6, R_CASE).translate([0.8, 0.8])).translate(
            [MUR_EXT + x + 1, MUR_EXT + y + 1])
        blancs.append(extr(cadre, z_int))
    noms_int = Manifold.batch_boolean(blancs, OpType.Add)

    # FACE EXTÉRIEURE : badge blanc (logo 42 AERO PARIS, « STORK VTOL », quadplane en noir)
    # et, dessous, le nom de la boîte en grand, en blanc sur le bleu.
    bw = W - 16
    bh = min(0.45 * D, 62.0)
    nh = min(0.2 * D, 22.0)
    total = bh + 6 + nh
    by = (D - total) / 2 + nh + 6                 # badge côté arrière
    bx = 8.0
    badge = rrect(bw, bh, 5).translate([bx, by])
    hl = bh - 10
    logo = decor.logo_cs(hauteur=hl, largeur=0.3 * bw)
    lw = logo.bounds()[2] - logo.bounds()[0]
    drone = decor.drone_cs(hauteur=hl, largeur=0.3 * bw)
    dw = drone.bounds()[2] - drone.bounds()[0]
    yc = by + bh / 2
    logo = logo.translate([bx + 6 + lw / 2, yc])
    drone = drone.translate([bx + bw - 6 - dw / 2, yc])
    zone_titre = bw - lw - dw - 28
    cs_t, t = texte_cs("STORK\nVTOL", zone_titre, bh * 0.45, 11.0)
    noir_cs = logo + drone + cs_t.translate([bx + 6 + lw + 8 + zone_titre / 2, yc])
    noirs = extr(noir_cs, z_ext)
    nom = b["titre"].split(" - ", 1)[-1]
    nom = {"ELECTRONIQUE": "ÉLECTRONIQUE", "HELICES": "HÉLICES"}.get(nom, nom)
    cs_n, t = texte_cs(nom, bw, nh, 22.0)
    TAILLES.append(t)
    nom_blanc = extr(cs_n.translate([W / 2, (D - total) / 2 + nh / 2]), z_ext)
    badge_blanc = extr(badge, z_ext) - noirs + nom_blanc

    incrust_noir = couv ^ noirs
    incrust_c = couv ^ (noms_int + badge_blanc)
    # version une couleur (STL) : tout gravé, contour du badge en creux
    contour = badge - rrect(bw - 1.6, bh - 1.6, 4.2).translate([bx + 0.8, by + 0.8])
    couv_mono = couv - Manifold.batch_boolean([noms_int, noirs, nom_blanc, extr(contour, z_ext)], OpType.Add)
    couv = couv - noms_int - badge_blanc - noirs

    # charnière arrière et loquets avant
    plus_b, trous_b = fermeture.ajouts_boite(W, D, H)
    corps = corps + plus_b - trous_b
    plus_c, trous_c = fermeture.ajouts_couvercle(W, D, H, COUV_EP)
    couv = couv + plus_c - trous_c
    couv_mono = couv_mono + plus_c - trous_c

    ASSEMBLAGE[b["fichier"]] = (corps, couv, W, D, H)   # couvercle en place (contrôles)

    # retourner pour l'impression (dessus sur le plateau) : rotation 180° autour de X
    pieces = [p.rotate([180, 0, 0]) for p in (couv, incrust_c, incrust_noir, couv_mono)]
    bb = pieces[0].bounding_box()
    couv, incrust_c, incrust_noir, couv_mono = [p.translate([-bb[0], -bb[1], -bb[2]]) for p in pieces]
    return corps, couv, (W, D, H), liste, incrust_b, incrust_c, incrust_noir, couv_mono


def maillage(man):
    m = man.to_mesh()
    return np.asarray(m.vert_properties)[:, :3].astype(float), np.asarray(m.tri_verts).astype(int)


def exporter(man, chemin):
    v, f = maillage(man)
    tm = trimesh.Trimesh(vertices=v, faces=f, process=False)
    tm.export(chemin)
    return tm


def exporter_3mf(chemin, nom, pieces, plateau=256.0):
    """3MF à plusieurs pièces (une couleur par pièce) lisible par Bambu Studio.
    pieces = [(nom_piece, manifold, emplacement_ams), ...]"""
    verts, tris, plages, off = [], [], [], 0
    for nom_p, man, ams in pieces:
        v, f = maillage(man)
        debut = sum(len(t) for t in tris)
        verts.append(v); tris.append(f + off); off += len(v)
        plages.append((nom_p, debut, debut + len(f) - 1, ams))
    V = np.vstack(verts); T = np.vstack(tris)
    # centrer sur le plateau
    c = (V.min(0) + V.max(0)) / 2
    V = V - [c[0] - plateau / 2, c[1] - plateau / 2, V[:, 2].min()]
    vx = "\n".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{z:.4f}"/>' for a, b, z in V)
    tx = "\n".join(f'<triangle v1="{a}" v2="{b}" v3="{d}"/>' for a, b, d in T)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
             f'<metadata name="Title">{nom}</metadata>\n<resources>\n'
             f'<object id="1" type="model" name="{nom}"><mesh><vertices>\n{vx}\n</vertices>'
             f'<triangles>\n{tx}\n</triangles></mesh></object>\n'
             '</resources>\n<build><item objectid="1"/></build>\n</model>\n')
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>', '  <object id="1">',
           f'    <metadata key="name" value="{nom}"/>',
           f'    <metadata key="extruder" value="{pieces[0][2]}"/>']
    for nom_p, a, z, ams in plages:
        cfg += [f'    <volume firstid="{a}" lastid="{z}">',
                f'      <metadata key="name" value="{nom_p}"/>',
                f'      <metadata key="extruder" value="{ams}"/>',
                '    </volume>']
    cfg += ['  </object>', '</config>', '']
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>\n')
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", "\n".join(cfg))
    return plages


if __name__ == "__main__":
    racine = os.path.dirname(os.path.abspath(__file__))
    dossier = os.path.join(racine, "stl")
    d3mf = os.path.join(racine, "3mf_bambu_tricolore")
    os.makedirs(dossier, exist_ok=True)
    os.makedirs(d3mf, exist_ok=True)
    for b in BOITES:
        corps, couv, (W, D, H), liste, inc_b, inc_c, inc_n, couv_mono = boite_et_couvercle(b)
        # STL monochromes (textes gravés en creux) : Neptune ou impression 1 couleur
        t1 = exporter(corps, os.path.join(dossier, f"{b['fichier']}_boite.stl"))
        t2 = exporter(couv_mono, os.path.join(dossier, f"{b['fichier']}_couvercle.stl"))
        e = couv.bounding_box()
        print(f"{b['fichier']:<20} boîte {W:.0f}x{D:.0f}x{H:.0f} mm  "
              f"couvercle {e[3]-e[0]:.0f}x{e[4]-e[1]:.0f}x{e[5]-e[2]:.1f} mm  "
              f"{len(liste)} cases  étanche={t1.is_watertight and t2.is_watertight}  "
              f"vol={(t1.volume + t2.volume)/1000:.0f} cm3")
        if b["fichier"] in BAMBU:
            exporter_3mf(os.path.join(d3mf, f"{b['fichier']}_boite.3mf"), f"{b['fichier']}_boite",
                         [("boite (noir)", corps, AMS_NOIR), ("textes (blanc)", inc_b, AMS_BLANC)])
            exporter_3mf(os.path.join(d3mf, f"{b['fichier']}_couvercle.3mf"), f"{b['fichier']}_couvercle",
                         [("couvercle (bleu)", couv, AMS_BLEU), ("plan + bandeau (blanc)", inc_c, AMS_BLANC),
                          ("logo + drone + titre (noir)", inc_n, AMS_NOIR)])
    # loquets (noir) : 2 par boîte, identiques pour toutes les boîtes
    lq = fermeture.loquet_impression()
    bb = lq.bounding_box()
    pas_x, pas_y = bb[3] - bb[0] + 6, bb[4] - bb[1] + 6
    for n, (nx, ny) in {"x2": (2, 1), "x14": (7, 2)}.items():
        plaque = Manifold.batch_boolean([lq.translate([i * pas_x, j * pas_y, 0])
                                         for i in range(nx) for j in range(ny)], OpType.Add)
        exporter(plaque, os.path.join(dossier, f"loquets_{n}.stl"))
        exporter_3mf(os.path.join(d3mf, f"loquets_{n}.3mf"), f"loquets_{n}", [("loquets (noir)", plaque, AMS_NOIR)])
    print(f"loquet : {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm")
    print(f"taille de texte mini : {min(TAILLES):.2f} mm")
