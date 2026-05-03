import cv2
import numpy as np

class Watermarker:
    """
    Classe experte en sécurité des images. Permet d'insérer un tatouage numérique 
    (watermark) dans le domaine fréquentiel via la Transformée en Cosinus Discrète (DCT).
    Ce type de tatouage est plus discret et plus robuste face aux compressions.
    """
    def __init__(self, alpha=0.1):
        """
        :param alpha: Cœfficient d'opacité du tatouage. 
                      0.1 garantit un tatouage subtil (presque invisible), 
                      augmenter la valeur rendra la marque plus apparente.
        """
        self.alpha = alpha

    def apply_dct_watermark(self, image, text):
        """
        Applique un texte en filigrane sur le canal bleu de l'image.
        
        :param image: L'image source à protéger (matrice NumPy BGR).
        :param text: La chaîne de caractères à insérer (ex: Date + ID Caméra).
        :return: L'image protégée (tatouée).
        """
        if image is None:
            return None

        # 1. Vérification et ajustement des dimensions
        # L'algorithme DCT d'OpenCV requiert obligatoirement des dimensions paires.
        h, w = image.shape[:2]
        if h % 2 != 0 or w % 2 != 0:
            # On soustrait 1 pixel si la dimension est impaire
            h = h if h % 2 == 0 else h - 1
            w = w if w % 2 == 0 else w - 1
            image = cv2.resize(image, (w, h))

        # 2. Séparation des canaux de couleurs
        # On extrait les canaux Bleu (B), Vert (G) et Rouge (R).
        # On va tatouer uniquement le canal Bleu car l'œil humain y est le moins sensible.
        b, g, r = cv2.split(image)

        # 3. Conversion du canal de destination en nombre à virgule flottante
        b_float = np.float32(b)

        # 4. Transformée DCT (Discrete Cosine Transform)
        # On passe du domaine spatial (pixels) au domaine fréquentiel (ondes).
        dct_b = cv2.dct(b_float)

        # 5. Création du masque contenant le texte
        # Matrice noire (zéros) de la même taille que l'image, en type float32.
        mask = np.zeros((h, w), dtype=np.float32)
        
        # Configuration visuelle du texte
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # Calcul des coordonnées pour centrer parfaitement le texte
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (w - text_size[0]) // 2
        text_y = (h + text_size[1]) // 2
        
        # Écriture du texte en blanc pur (255) sur le masque noir
        cv2.putText(mask, text, (text_x, text_y), font, font_scale, 255, thickness)

        # 6. Insertion mathématique du tatouage
        # On additionne le masque de texte (atténué par alpha) aux fréquences de l'image
        dct_b_marked = dct_b + (self.alpha * mask)

        # 7. Transformée DCT Inverse
        # On repasse du domaine fréquentiel au domaine spatial (pixels).
        idct_b = cv2.idct(dct_b_marked)

        # 8. Re-normalisation
        # On s'assure qu'aucune valeur de pixel ne dépasse 255 ou n'est sous 0,
        # puis on reconvertit en entiers 8 bits (format standard d'image).
        b_marked = np.clip(idct_b, 0, 255).astype(np.uint8)

        # 9. Reconstruction de l'image finale
        # On fusionne le canal Bleu tatoué avec les canaux Vert et Rouge originaux intacts.
        watermarked_image = cv2.merge((b_marked, g, r))

        return watermarked_image
