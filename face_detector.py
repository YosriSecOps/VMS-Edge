import cv2

class FaceDetector:
    """
    Classe dédiée à la détection de visages en temps réel à l'aide 
    de la méthode des cascades de Haar fournie par OpenCV.
    """
    def __init__(self):
        # 1. Chargement du modèle Haar Cascade pour les visages de face.
        # Le chemin cv2.data.haarcascades pointe vers le dossier interne d'OpenCV
        # contenant les modèles pré-entraînés.
        model_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(model_path)

    def detect(self, frame):
        """
        2. Analyse l'image fournie pour y détecter des visages.
        
        :param frame: Image capturée par OpenCV (format BGR).
        :return: Liste de coordonnées (x, y, w, h) pour chaque visage détecté.
                 Retourne une liste vide si aucun visage n'est détecté.
        """
        # Vérification de sécurité au cas où l'image serait vide
        if frame is None:
            return []

        # 3. Conversion de l'image en niveaux de gris.
        # Les algorithmes de type Haar fonctionnent sur les variations d'intensité lumineuse,
        # la couleur n'est donc pas nécessaire et ralentirait le processus.
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 4. Détection des visages à l'aide de detectMultiScale.
        # - scaleFactor=1.1 : Compense pour les visages plus ou moins proches de la caméra.
        # - minNeighbors=5 : Limite les faux positifs en exigeant un certain nombre de détections croisées.
        # - minSize=(30,30) : Ignore les détections de trop petite taille.
        faces = self.face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # OpenCV renvoie un numpy.ndarray. On le convertit en liste Python standard
        # contenant les coordonnées (x, y, largeur, hauteur).
        return list(faces)
