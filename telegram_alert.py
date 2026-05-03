import requests
import os

def send_telegram_alert(image_path, nom, statut, token, chat_id, camera_name="Webcam USB"):
    """
    Envoie une alerte avec photo sur Telegram via l'API.
    """
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    message = f"🚨 ALERTE SÉCURITÉ (Caméra: {camera_name}) : Détection d'une personne {statut} ! Nom : {nom}"
    
    if not os.path.exists(image_path):
        print(f"[TELEGRAM] Erreur: L'image de preuve {image_path} est introuvable sur le disque.")
        return False
        
    try:
        with open(image_path, "rb") as image_file:
            payload = {"chat_id": chat_id, "caption": message}
            files = {"photo": image_file}
            
            # Envoi de la requête POST à l'API Telegram
            response = requests.post(url, data=payload, files=files)
            
        if response.status_code == 200:
            print("[TELEGRAM] 📲 Alerte envoyée avec succès sur votre téléphone !")
            return True
        else:
            print(f"[TELEGRAM] Erreur d'envoi de l'alerte : {response.text}")
            return False
    except Exception as e:
        print(f"[TELEGRAM] Erreur critique réseau lors de l'envoi : {e}")
        return False
