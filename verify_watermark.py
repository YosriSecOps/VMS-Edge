import cv2
import numpy as np

def verify_watermark():
    """
    Outil forensique pour extraire et révéler le tatouage numérique (watermark) 
    caché dans le domaine fréquentiel (DCT) d'une image sécurisée.
    """
    print("=== Outil de Vérification de Tatouage Numérique ===")
    
    # 2. Demander à l'utilisateur de saisir le chemin de l'image
    image_path = input("Entrez le chemin de l'image tatouée (ex: captures/log_YYYYMMDD_HHMMSS.jpg) : ")
    
    # 3. Charger l'image depuis le disque
    image = cv2.imread(image_path)
    
    # Vérification que l'image a bien été chargée
    if image is None:
        print(f"[ERREUR] Impossible de charger l'image à partir du chemin : '{image_path}'. Vérifiez le nom du fichier.")
        return

    print("[INFO] Image chargée avec succès. Analyse des fréquences en cours...")

    # 4. Séparation des canaux (B, G, R) et isolation du canal Bleu (B)
    # On sait que notre système insère le tatouage uniquement dans le canal Bleu 
    # pour une invisibilité maximale.
    b, g, r = cv2.split(image)
    b_float = np.float32(b)

    # 5. Application de la transformée DCT
    # On repasse du domaine spatial (pixels) au domaine fréquentiel pour retrouver le masque caché.
    dct_b = cv2.dct(b_float)

    # 6. Révélation du tatouage caché
    # On prend la valeur absolue des coefficients DCT.
    dct_abs = np.abs(dct_b)
    
    # Astuce cruciale : Le premier coefficient DCT (à la position 0,0) est la composante continue (DC).
    # Elle représente l'intensité moyenne de l'image et sa valeur est gigantesque par rapport au reste.
    # On la met à zéro pour empêcher qu'elle "n'écrase" le contraste de notre texte tatoué 
    # lors de la normalisation.
    dct_abs[0, 0] = 0

    # Ajustement de contraste : On normalise la matrice DCT modifiée sur une échelle de 0 à 255 
    # (pixels classiques en 8 bits) afin de rendre l'image affichable sur un écran.
    watermark_visual = cv2.normalize(dct_abs, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # Amélioration supplémentaire : l'égalisation d'histogramme aide à étirer le contraste
    # et fait ressortir les pixels clairs (notre texte) sur le fond sombre des hautes fréquences.
    watermark_enhanced = cv2.equalizeHist(watermark_visual)

    print("[SUCCÈS] Extraction terminée. Affichage du résultat.")
    print("--> Appuyez sur n'importe quelle touche dans la fenêtre d'image pour quitter.")

    # 7. Affichage de la matrice transformée
    cv2.imshow("Tatouage Numérique Révélé", watermark_enhanced)
    
    # Attente d'une action utilisateur pour fermer la fenêtre proprement
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    verify_watermark()
