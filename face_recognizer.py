import cv2
import numpy as np
import json

class FaceRecognizer:
    """
    Classe destinée à la reconnaissance faciale basée sur l'algorithme LBPH.
    Cette version lit dynamiquement les identités depuis le fichier 'users.json' 
    et applique un seuil strict pour éviter les faux positifs.
    """
    def __init__(self):
        # Création de l'instance du modèle LBPH
        self.model = cv2.face.LBPHFaceRecognizer_create()
        
        # Charger le modèle entraîné (cerveau)
        try:
            self.model.read('trainer.yml')
        except cv2.error:
            print("[ATTENTION] Fichier 'trainer.yml' introuvable. Le modèle ne reconnaîtra personne.")

        # 3. Charger le fichier JSON contenant les données des utilisateurs enregistrés
        # Remplace les anciens dictionnaires codés en dur.
        try:
            with open("users.json", "r", encoding="utf-8") as f:
                self.users_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("[ATTENTION] Fichier 'users.json' introuvable ou vide.")
            self.users_data = {}

    def identify(self, face_image):
        """
        Identifie un visage recadré et retourne son Nom/CIN et son statut.
        
        :param face_image: Image du visage (doit être en niveaux de gris et recadrée).
        :return: Un tuple (nom_affiche, statut, confiance).
        """
        try:
            # LBPH retourne un ID numérique et une "distance" (confiance)
            id_predict, confidence = self.model.predict(face_image)
        except cv2.error:
            # Cas où le modèle n'a jamais été entraîné
            return ("Inconnu", "inconnu", 100.0)
            
        # 4. Vérification du seuil strict de distance
        if confidence < 50:
            # 5. Si la distance est faible, le visage est reconnu.
            # Les clés d'un fichier JSON sont toujours des chaînes de caractères (str).
            str_id = str(id_predict)
            
            # On vérifie si l'ID renvoyé par le modèle existe bien dans notre base JSON
            if str_id in self.users_data:
                user_info = self.users_data[str_id]
                nom = user_info.get("nom", "Inconnu")
                cin = user_info.get("cin", "N/A")
                statut = user_info.get("statut", "inconnu")
                
                # Formatage du nom d'affichage avec le CIN
                nom_affiche = f"{nom} - {cin}"
            else:
                # L'ID prédit n'est pas dans le JSON (peut arriver si le fichier a été vidé manuellement)
                nom_affiche = "Inconnu"
                statut = "inconnu"
        else:
            # 6. La distance est trop élevée. On force l'anonymat pour éviter un faux positif.
            nom_affiche = "Inconnu"
            statut = "inconnu"
            
        # 7. Retour systématisé
        return (nom_affiche, statut, confidence)
