import cv2
import numpy as np
import os
from PIL import Image

def get_images_and_labels(path):
    """
    3. Parcourt le dossier spécifié, extrait les visages et leurs IDs respectifs.
    
    :param path: Chemin vers le dossier contenant les images ('dataset')
    :return: Un tuple (liste_des_visages_numpy, liste_des_ids)
    """
    # Obtenir la liste de tous les fichiers .jpg dans le dossier
    image_paths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]
    
    faces = []
    ids = []
    
    for image_path in image_paths:
        # Ouvrir l'image avec PIL (Python Imaging Library) et la convertir en niveaux 
        # de gris ('L' signifie Luminance). C'est une sécurité supplémentaire pour être sûr
        # du format, même si les images ont été sauvegardées en gris.
        pil_image = Image.open(image_path).convert('L')
        
        # Convertir l'objet image PIL en tableau numpy (exigé par OpenCV)
        # 'uint8' est le format standard pour les pixels d'une image (0 à 255)
        image_np = np.array(pil_image, 'uint8')
        
        # Le nom du fichier est du format : User.[ID].[Compteur].jpg
        # Ex: User.1.25.jpg -> on récupère '1'
        filename = os.path.split(image_path)[-1]
        user_id = int(filename.split(".")[1])
        
        # Ajouter le visage au tableau et l'ID à la liste
        faces.append(image_np)
        ids.append(user_id)
        
    return faces, ids

def main():
    print("\n[INFO] Démarrage de l'extraction des données et de l'entraînement...")
    
    # 2. Initialisation du modèle LBPH d'OpenCV
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # Définition du chemin où se trouvent nos captures
    dataset_path = 'dataset'
    
    # 4. Exécuter notre fonction d'extraction
    faces, ids = get_images_and_labels(dataset_path)
    
    # Vérification de sécurité au cas où le dossier est vide
    if not faces or not ids:
        print("[ERREUR] Aucune image trouvée dans le dossier 'dataset'.")
        return
        
    # 5. Lancer l'entraînement du modèle LBPH
    # La méthode train() attend une liste d'images et un tableau numpy (np.array) pour les labels
    recognizer.train(faces, np.array(ids))
    
    # 6. Sauvegarder le modèle "cerveau" entraîné dans un fichier yml
    recognizer.write('trainer.yml')
    
    # Afficher le bilan
    # np.unique permet de compter le nombre d'IDs différents (le nombre de personnes)
    unique_ids = len(np.unique(ids))
    print(f"\n[INFO] Succès ! {unique_ids} visage(s) différent(s) entraîné(s).")
    print(f"[INFO] Le modèle a été sauvegardé dans le fichier 'trainer.yml'.")

if __name__ == "__main__":
    main()
