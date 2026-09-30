# === Imports ===
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
from PIL import Image, ImageTk
from scipy.signal import convolve2d
from scipy.ndimage import gaussian_filter, uniform_filter

# === Variables globales ===
photo = None
img = None
canvas = None
matrice_pixels = None
image2_fusion = None
dialogues = {}
array_liste = []
indice = -1
MAX_HISTORIQUE = 20


# === Fonctions d'interface utilisateur ===
def ouvrir_dialogue_slider(titre, from_, to, resolution, default, commande, appliquer_cb, annuler_cb):
    dialogue = tk.Toplevel(fenetre)
    dialogue.title(titre)
    dialogue.geometry("300x150")
    dialogue.grab_set()

    slider = tk.Scale(dialogue, from_=from_, to=to, orient=tk.HORIZONTAL,
                      length=200, resolution=resolution, command=commande)
    slider.set(default)
    slider.pack(pady=20)

    frame_boutons = tk.Frame(dialogue)
    frame_boutons.pack(side=tk.BOTTOM, pady=10)

    tk.Button(frame_boutons, text="Appliquer", command=appliquer_cb).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_boutons, text="Annuler", command=annuler_cb).pack(side=tk.LEFT, padx=10)

    dialogue.protocol("WM_DELETE_WINDOW", annuler_cb)
    return dialogue


def dialogue_clear(cle):
    """Ferme et supprime une boîte de dialogue (cle = clé dans le dictionnaire dialogues)."""
    dialogue = dialogues.pop(cle, None)
    if dialogue is not None:
        dialogue.destroy()


def valider_effet(cle):
    """Valide l'aperçu en cours : l'image affichée devient l'image de référence."""
    global matrice_pixels, image2_fusion
    if img is not None:
        matrice_pixels = np.array(img)
        maj_historique()
    image2_fusion = None
    dialogue_clear(cle)


def annuler_effet(cle):
    """Annule l'aperçu en cours et revient à l'image de référence."""
    global img, image2_fusion
    if matrice_pixels is not None:
        img = Image.fromarray(matrice_pixels)
        afficher_image()
    image2_fusion = None
    dialogue_clear(cle)


# === Fonctions de gestion d'image ===
def charger_image():
    global img, matrice_pixels, array_liste, indice
    nom_fichier = filedialog.askopenfilename(title="Ouvrir une image")
    if not nom_fichier:
        return
    try:
        img = Image.open(nom_fichier).convert('RGB')
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir l'image :\n{e}")
        return
    matrice_pixels = np.array(img)

    array_liste = []
    indice = -1
    maj_historique()
    afficher_image()


def afficher_image():
    global photo, canvas
    if img is not None:
        photo = ImageTk.PhotoImage(img)
        if canvas is None:
            canvas = tk.Canvas(fenetre, bg="white")
            canvas.pack(fill=tk.BOTH, expand=True)
            canvas.bind("<Configure>", centrer_image)
        centrer_image()


def centrer_image(event=None):
    if img is not None and photo is not None and canvas is not None:
        canvas.delete("all")
        x = (canvas.winfo_width() - photo.width()) // 2
        y = (canvas.winfo_height() - photo.height()) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=photo)


def appliquer_image(nouvelle_matrice):
    global matrice_pixels, img
    matrice_pixels = np.ascontiguousarray(nouvelle_matrice)
    img = Image.fromarray(matrice_pixels)
    maj_historique()
    afficher_image()


# === Filtres ===
def appliquer_filtre(filtre):
    """Applique une fonction de filtre à l'image actuelle."""
    if matrice_pixels is None:
        return
    appliquer_image(filtre(matrice_pixels))


def filtre_vert(matrice):
    """Ne conserve que le canal vert."""
    res = matrice.copy()
    res[:, :, [0, 2]] = 0
    return res


def filtre_gris(matrice):
    """Niveaux de gris (moyenne des canaux)."""
    gris = np.mean(matrice[:, :, :3], axis=2, keepdims=True).astype(np.uint8)
    return np.repeat(gris, 3, axis=2)


def filtre_negatif(matrice):
    return 255 - matrice


def filtre_symetrie(matrice):
    return np.ascontiguousarray(matrice[:, ::-1])


def detection_bords():
    if matrice_pixels is None:
        return
    gray = np.mean(matrice_pixels, axis=2)
    gray_blurred = gaussian_filter(gray, sigma=1)
    sobelX = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobelY = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    gx = convolve2d(gray_blurred, sobelX, mode='same', boundary='symm')
    gy = convolve2d(gray_blurred, sobelY, mode='same', boundary='symm')
    G = np.hypot(gx, gy)

    if G.max() > 0:
        G = (G / G.max()) * 255
    seuil = 30
    G = np.where(G >= seuil, 255, 0)
    edge_img = np.stack([G] * 3, axis=-1).astype(np.uint8)
    appliquer_image(edge_img)


# === Fusion ===
def ajuster_fusion(valeur):
    """Fusion progressive (0 = image principale, 100 = image secondaire)."""
    global img
    if image2_fusion is None or matrice_pixels is None:
        return
    ratio = float(valeur) / 100.0
    pixels_fusion = matrice_pixels * (1.0 - ratio) + image2_fusion * ratio
    img = Image.fromarray(pixels_fusion.astype(np.uint8))
    afficher_image()


def regler_fusion():
    global image2_fusion
    if img is None:
        return
    chemin_image2 = filedialog.askopenfilename(title="Choisir une image à fusionner")
    if not chemin_image2:
        return
    image2 = Image.open(chemin_image2).convert('RGB').resize(img.size)
    image2_fusion = np.array(image2)
    dialogues["fusion"] = ouvrir_dialogue_slider(
        titre="Fusion d'images", from_=0, to=100, resolution=1, default=50,
        commande=ajuster_fusion,
        appliquer_cb=lambda: valider_effet("fusion"),
        annuler_cb=lambda: annuler_effet("fusion"),
    )
    ajuster_fusion(50)  # aperçu immédiat à la valeur par défaut


# === Luminosité ===
def ajuster_luminosite(valeur):
    """Facteur < 1 : assombrit ; 1 : inchangé ; > 1 : éclaircit."""
    global img
    if matrice_pixels is None:
        return
    facteur = float(valeur)
    matrice_ajustee = np.clip(matrice_pixels.astype(np.float32) * facteur, 0, 255).astype(np.uint8)
    img = Image.fromarray(matrice_ajustee)
    afficher_image()


def regler_luminosite():
    if matrice_pixels is None:
        return
    dialogues["luminosite"] = ouvrir_dialogue_slider(
        titre="Luminosité", from_=0.0, to=2.0, resolution=0.1, default=1.0,
        commande=ajuster_luminosite,
        appliquer_cb=lambda: valider_effet("luminosite"),
        annuler_cb=lambda: annuler_effet("luminosite"),
    )


# === Pixellisation ===
def ajuster_pixellisation(valeur):
    global img
    if matrice_pixels is None:
        return
    facteur = np.clip(float(valeur), 0.0, 1.0)
    taille_max = 50
    taille_bloc = int(1 + facteur * (taille_max - 1))
    h, w = matrice_pixels.shape[:2]

    petite = Image.fromarray(matrice_pixels).resize(
        (max(1, w // taille_bloc), max(1, h // taille_bloc)), Image.NEAREST)
    img = petite.resize((w, h), Image.NEAREST)
    afficher_image()


def regler_pixellisation():
    if matrice_pixels is None:
        return
    dialogues["pixellisation"] = ouvrir_dialogue_slider(
        titre="Pixellisation", from_=0.0, to=1.0, resolution=0.01, default=0.0,
        commande=ajuster_pixellisation,
        appliquer_cb=lambda: valider_effet("pixellisation"),
        annuler_cb=lambda: annuler_effet("pixellisation"),
    )


# === Contraste ===
def ajuster_contraste(valeur=None):
    """Contraste par courbe sigmoïde (c = contraste, k = pente)."""
    global img
    if matrice_pixels is None or "contraste" not in dialogues:
        return
    c = slider_contraste.get()
    k = slider_pente.get()
    img_norm = matrice_pixels / 255.0

    def sigmoide(x):
        return 1 / (1 + np.exp(-k * c * (x - 0.5)))


    s0, s1 = sigmoide(0.0), sigmoide(1.0)
    resultat = (sigmoide(img_norm) - s0) / (s1 - s0) * 255
    img = Image.fromarray(np.clip(resultat, 0, 255).astype(np.uint8))
    afficher_image()


def regler_contraste():
    global slider_contraste, slider_pente
    if matrice_pixels is None:
        return

    dialogue = tk.Toplevel(fenetre)
    dialogue.title("Contraste")
    dialogue.geometry("300x250")
    dialogue.grab_set()
    dialogues["contraste"] = dialogue

    slider_contraste = tk.Scale(dialogue, from_=0.1, to=5.0, resolution=0.1,
                                orient=tk.HORIZONTAL, label="Contraste", length=200)
    slider_contraste.set(1.0)
    slider_contraste.pack(pady=5)

    slider_pente = tk.Scale(dialogue, from_=1.0, to=20.0, resolution=1.0,
                            orient=tk.HORIZONTAL, label="Pente", length=200)
    slider_pente.set(10.0)
    slider_pente.pack(pady=5)

    slider_contraste.config(command=ajuster_contraste)
    slider_pente.config(command=ajuster_contraste)

    frame_boutons = tk.Frame(dialogue)
    frame_boutons.pack(side=tk.BOTTOM, pady=10)
    tk.Button(frame_boutons, text="Appliquer", command=lambda: valider_effet("contraste")).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_boutons, text="Annuler", command=lambda: annuler_effet("contraste")).pack(side=tk.LEFT, padx=10)
    dialogue.protocol("WM_DELETE_WINDOW", lambda: annuler_effet("contraste"))


# === Flou ===
def appliquer_flou(valeur):
    """Flou uniforme : moyenne sur un voisinage taille x taille."""
    global img
    if matrice_pixels is None:
        return
    taille = int(valeur)

    flou = uniform_filter(matrice_pixels.astype(np.float32), size=(taille, taille, 1), mode='reflect')
    img = Image.fromarray(np.clip(flou, 0, 255).astype(np.uint8))
    afficher_image()


def regler_flou():
    if matrice_pixels is None:
        return
    dialogues["flou"] = ouvrir_dialogue_slider(
        titre="Flou Uniforme", from_=1, to=15, resolution=1, default=1,
        commande=appliquer_flou,
        appliquer_cb=lambda: valider_effet("flou"),
        annuler_cb=lambda: annuler_effet("flou"),
    )


# === Flou Gaussien ===
def appliquer_flou_gaussien(valeur):
    """Noyau gaussien 3x3 appliqué `valeur` fois."""
    global img
    if matrice_pixels is None:
        return
    kernel = np.array([[1, 2, 1],
                       [2, 4, 2],
                       [1, 2, 1]]) / 16

    pixels_flous = matrice_pixels.astype(np.float32)
    for _ in range(int(valeur)):
        for i in range(3):
            pixels_flous[:, :, i] = convolve2d(pixels_flous[:, :, i], kernel,
                                               mode='same', boundary='symm')
    img = Image.fromarray(np.clip(pixels_flous, 0, 255).astype(np.uint8))
    afficher_image()


def regler_flou_gaussien():
    if matrice_pixels is None:  
        return
    dialogues["flou gaussien"] = ouvrir_dialogue_slider(
        titre="Flou Gaussien", from_=1, to=10, resolution=1, default=1,
        commande=appliquer_flou_gaussien,
        appliquer_cb=lambda: valider_effet("flou gaussien"),
        annuler_cb=lambda: annuler_effet("flou gaussien"),
    )


# === Sauvegardes ===
def demander_nom_fichier():
    if img is None:
        return
    filepath = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("Fichiers PNG", "*.png"), ("Fichiers JPEG", ("*.jpg", "*.jpeg"))],
        title="Enregistrer l'image"
    )
    if filepath:
        save_progress(filepath)


def save_progress(filepath):
    """Sauvegarde l'image actuelle dans un fichier."""
    ext = os.path.splitext(filepath)[1].lower()
    format_ = "JPEG" if ext in (".jpg", ".jpeg") else "PNG"
    img.save(filepath, format=format_)


# === Historique ===
def maj_menu_historique():
    menu_undo.entryconfig("annuler", state="normal" if indice > 0 else "disabled")
    menu_undo.entryconfig("refaire", state="normal" if indice < len(array_liste) - 1 else "disabled")


def maj_historique():
    """Ajoute l'état courant à l'historique (supprime les états 'refaire')."""
    global indice, array_liste
    del array_liste[indice + 1:]
    array_liste.append(matrice_pixels.copy())
    if len(array_liste) > MAX_HISTORIQUE:
        array_liste.pop(0)
    indice = len(array_liste) - 1
    maj_menu_historique()


def naviguer_historique(direction):
    """direction : "retour" (annuler) ou "avant" (refaire)."""
    global indice, matrice_pixels, img
    if dialogues:  
        return
    if direction == "retour" and indice > 0:
        indice -= 1
    elif direction == "avant" and indice < len(array_liste) - 1:
        indice += 1
    else:
        return
    matrice_pixels = array_liste[indice].copy()
    img = Image.fromarray(matrice_pixels)
    afficher_image()
    maj_menu_historique()


# === Interface GUI ===
fenetre = tk.Tk()
fenetre.title("Afficheur d'image")

try:
    fenetre.state("zoomed")
except tk.TclError:
    try:
        fenetre.attributes("-zoomed", True)
    except tk.TclError:
        fenetre.geometry("1000x700")

menu_principal = tk.Menu(fenetre)

# === Raccourcis ===
fenetre.bind('<Control-z>', lambda e: naviguer_historique("retour"))
fenetre.bind('<Control-y>', lambda e: naviguer_historique("avant"))  
fenetre.bind('<Control-s>', lambda e: demander_nom_fichier())

# === Fichier ===
menu_fichier = tk.Menu(menu_principal, tearoff=0)
menu_fichier.add_command(label="Ouvrir", command=charger_image)
menu_fichier.add_command(label="Sauvegarde", command=demander_nom_fichier)
menu_principal.add_cascade(label="Fichier", menu=menu_fichier)

# === Filtres Simples ===
menu_filtres = tk.Menu(menu_principal, tearoff=0)
menu_filtres.add_command(label="Filtre Vert", command=lambda: appliquer_filtre(filtre_vert))
menu_filtres.add_command(label="Filtre Gris", command=lambda: appliquer_filtre(filtre_gris))
menu_filtres.add_command(label="Négatif", command=lambda: appliquer_filtre(filtre_negatif))
menu_filtres.add_command(label="Symétrique", command=lambda: appliquer_filtre(filtre_symetrie))
menu_filtres.add_command(label="Fusion", command=regler_fusion)
menu_filtres.add_command(label="Filtre Detection de bords", command=detection_bords)
menu_principal.add_cascade(label="Filtres", menu=menu_filtres)

# === Filtres Paramétriques ===
menu_reglages = tk.Menu(menu_principal, tearoff=0)
menu_reglages.add_command(label="Luminosité", command=regler_luminosite)
menu_reglages.add_command(label="Contraste", command=regler_contraste)
menu_reglages.add_command(label="Flou", command=regler_flou)
menu_reglages.add_command(label="Flou gaussien", command=regler_flou_gaussien)
menu_reglages.add_command(label="Pixellisation", command=regler_pixellisation)
menu_principal.add_cascade(label="Réglages", menu=menu_reglages)

# === Historique ===
menu_undo = tk.Menu(menu_principal, tearoff=0)
menu_undo.add_command(label="annuler", command=lambda: naviguer_historique("retour"), state="disabled")
menu_undo.add_command(label="refaire", command=lambda: naviguer_historique("avant"), state="disabled")
menu_principal.add_cascade(label="Historique", menu=menu_undo)

fenetre.config(menu=menu_principal)
fenetre.mainloop()
