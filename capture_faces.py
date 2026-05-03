import cv2
import os
import json

def capture_faces():
    """
    Script utilitaire pour capturer et enregistrer des images de visages 
    afin de créer une base de données (dataset) pour l'entraînement du modèle LBPH.
    Gère les identités dynamiquement via un fichier 'users.json'.
    """
    
    # Vérification et création du dossier de destination des images
    dataset_dir = "dataset"
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        print(f"[INFO] Création du dossier '{dataset_dir}'.")

    # 3. Charger le fichier users.json ou créer un dictionnaire vide
    json_path = "users.json"
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                users_data = json.load(f)
            except json.JSONDecodeError:
                users_data = {}
    else:
        users_data = {}

    # 2. Demander les informations de l'utilisateur
    print("\n--- Enregistrement d'un nouvel utilisateur ---")
    nom = input("Entrez le Nom et Prénom de la personne : ")
    cin = input("Entrez le numéro de CIN (Carte d'Identité Nationale) : ")

    # 4. Déterminer le prochain ID numérique disponible
    if users_data:
        # On extrait les clés (qui sont des strings dans JSON), on les convertit 
        # en entiers, on prend le maximum, et on ajoute 1.
        nouvel_id = max(int(k) for k in users_data.keys()) + 1
    else:
        # Si le fichier est vide ou n'existe pas, on commence à l'ID 1
        nouvel_id = 1

    # 5. Ajouter le nouvel utilisateur au dictionnaire
    users_data[str(nouvel_id)] = {
        "nom": nom,
        "cin": cin,
        "statut": "autorisé" # Par défaut, on le met "autorisé"
    }

    # 6. Sauvegarder les données mises à jour dans le fichier users.json
    with open(json_path, "w", encoding="utf-8") as f:
        # On utilise indent=4 pour rendre le fichier lisible par un humain
        # et ensure_ascii=False pour supporter les caractères accentués
        json.dump(users_data, f, indent=4, ensure_ascii=False)
        
    print(f"\n[INFO] Utilisateur '{nom}' enregistré avec succès sous l'ID {nouvel_id}.")

    # Chargement du modèle OpenCV (Haar Cascade) pour la détection de visages
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_detector = cv2.CascadeClassifier(cascade_path)

    # Ouverture du flux vidéo (webcam)
    print("\n[INFO] Initialisation de la caméra. Regardez l'objectif de la webcam...")
    cap = cv2.VideoCapture(0)

    count = 0  # Initialisation du compteur d'images

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERREUR] Impossible de lire le flux de la caméra.")
            break

        # Convertir l'image en niveaux de gris
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Détecter les visages sur la frame actuelle
        faces = face_detector.detectMultiScale(
            gray_frame, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )

        for (x, y, w, h) in faces:
            count += 1
            
            # Extraire la région du visage (ROI)
            face_roi = gray_frame[y:y+h, x:x+w]
            
            # 7. Sauvegarder l'image en utilisant le nouvel ID généré
            file_name = f"User.{nouvel_id}.{count}.jpg"
            file_path = os.path.join(dataset_dir, file_name)
            
            cv2.imwrite(file_path, face_roi)
            
            # Dessiner un rectangle bleu autour du visage
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            print(f"Image {count}/50 sauvegardée : {file_name}")
            
            # On arrête la boucle for ici pour ne sauvegarder que le premier visage détecté
            break

        # Afficher le retour caméra
        cv2.imshow("Capture des visages - Appuyez sur 'q' pour quitter", frame)

        # Conditions d'arrêt
        key = cv2.waitKey(100) & 0xFF
        if key == ord('q'):
            print("\n[INFO] Capture interrompue manuellement par l'utilisateur.")
            break
        
        if count >= 50:
            print(f"\n[INFO] L'acquisition de données est terminée pour {nom} (50 images).")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_faces()
