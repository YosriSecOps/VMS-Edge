import customtkinter as ctk
import cv2
import threading
import time
import os
import datetime
from collections import Counter
from PIL import Image

# Importation des modules existants de votre projet
from face_detector import FaceDetector
from face_recognizer import FaceRecognizer
from db_manager import DBManager
from watermarker import Watermarker
from telegram_alert import send_telegram_alert

TELEGRAM_TOKEN = "VOTRE_TOKEN_TELEGRAM_ICI"
TELEGRAM_CHAT_ID = "VOTRE_CHAT_ID_ICI"

class SmartSurveillanceApp(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 1. Initialisation des composants IA et Base de données
        print("[INFO] Chargement des modèles IA...")
        # Pour le Multithreading, chaque caméra doit avoir son propre modèle de détection en RAM
        self.face_detector_usb = FaceDetector()
        self.face_recognizer_usb = FaceRecognizer()
        self.face_detector_ip = FaceDetector()
        self.face_recognizer_ip = FaceRecognizer()
        self.db_manager = DBManager()
        self.watermarker = Watermarker(alpha=0.1)
        
        # Dossier de captures pour le logging
        self.captures_dir = "captures"
        if not os.path.exists(self.captures_dir):
            os.makedirs(self.captures_dir)
            
        # 2. Buffers de lissage temporel et Cooldowns (Totalement indépendants par caméra)
        self.buffer_usb = []
        self.buffer_ip = []
        self.last_capture_usb = 0
        self.last_capture_ip = 0
        
        # 3. Interface Tkinter (Côte à côte)
        self.video_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.video_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.video_frame.grid_columnconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(1, weight=1)
        
        # Caméra USB
        self.label_usb_title = ctk.CTkLabel(self.video_frame, text="Webcam USB (Locale)", font=("Helvetica", 16, "bold"), text_color="#3484F0")
        self.label_usb_title.grid(row=0, column=0, pady=(0, 10))
        self.video_label_usb = ctk.CTkLabel(self.video_frame, text="En attente du flux USB...", font=("Helvetica", 14), bg_color="#1E1E1E", width=480, height=360)
        self.video_label_usb.grid(row=1, column=0, padx=10)
        
        # Caméra IP
        self.label_ip_title = ctk.CTkLabel(self.video_frame, text="Smartphone IP (Réseau)", font=("Helvetica", 16, "bold"), text_color="#28A745")
        self.label_ip_title.grid(row=0, column=1, pady=(0, 10))
        self.video_label_ip = ctk.CTkLabel(self.video_frame, text="En attente du flux IP...", font=("Helvetica", 14), bg_color="#1E1E1E", width=480, height=360)
        self.video_label_ip.grid(row=1, column=1, padx=10)
        
        # 4. Sources vidéo
        print("[INFO] Démarrage des flux vidéo réseau et local...")
        self.cap_usb = cv2.VideoCapture(0)
        self.cap_ip = cv2.VideoCapture("http://192.168.1.141:4747/video")
        
        # Images partagées (annotées par l'IA) prêtes pour l'affichage
        self.annotated_frame_usb = None
        self.annotated_frame_ip = None
        self.running = True

        # 5. Multithreading : Lancement des cœurs de calcul IA
        self.thread_usb = threading.Thread(target=self.process_usb_loop, daemon=True)
        self.thread_ip = threading.Thread(target=self.process_ip_loop, daemon=True)
        self.thread_usb.start()
        self.thread_ip.start()

        # Boucle d'affichage Tkinter
        self.update_video_labels()

    def _process_frame_ai(self, frame, cam_id, cam_name, detection_buffer, last_capture_time, detector, recognizer):
        """Méthode Moteur : Applique le pipeline de détection complet sur une image."""
        clean_frame = frame.copy()
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # A. Détection des visages (Haar Cascade)
        faces = detector.detect(frame)
        
        # Reset dynamique du lissage si personne n'est devant la caméra
        if len(faces) == 0:
            detection_buffer.clear()
            return frame, last_capture_time
            
        captured_this_frame = False
        current_time = time.time()
        
        # B. Reconnaissance LBPH sur chaque visage
        for (x, y, w, h) in faces:
            face_roi = gray_frame[y:y+h, x:x+w]
            nom_brut, statut_brut, confiance = recognizer.identify(face_roi)
            
            detection_buffer.append((nom_brut, statut_brut))
            
            # C. Lissage temporel (Vote Majoritaire sur 20 frames = ~1 seconde)
            if len(detection_buffer) > 20:
                detection_buffer.pop(0)
                
            if len(detection_buffer) < 20:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
                cv2.putText(frame, "Analyse...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            else:
                noms_seulement = [item[0] for item in detection_buffer]
                statuts_seulement = [item[1] for item in detection_buffer]
                nom_final = Counter(noms_seulement).most_common(1)[0][0]
                statut_final = Counter(statuts_seulement).most_common(1)[0][0]
                
                # Interface visuelle
                color = (0, 255, 0) if statut_final == "autorisé" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                text = f"{nom_final} ({statut_final})"
                cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # D. Alertes, SQLite et Watermark (Délai de 5 sec pour ne pas spam)
                if not captured_this_frame and (current_time - last_capture_time > 5):
                    if statut_final in ["non autorisé", "inconnu"]:
                        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        img_filename = f"log_{cam_id}_{now_str}.jpg"
                        img_path = os.path.join(self.captures_dir, img_filename)
                        
                        # Sauvegarde image propre + Tatouage DCT
                        watermarked_img = self.watermarker.apply_dct_watermark(clean_frame, f"{now_str} {cam_id}")
                        cv2.imwrite(img_path, watermarked_img if watermarked_img is not None else clean_frame)
                        
                        # Injection dans SQLite avec le nom précis de la source
                        self.db_manager.log_event(cam_id, statut_final, img_path, camera_name=cam_name)
                        
                        # Alerte Telegram envoyée dans un micro-thread pour NE PAS bloquer la vidéo
                        threading.Thread(
                            target=send_telegram_alert, 
                            args=(img_path, nom_final, statut_final, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID), 
                            daemon=True
                        ).start()
                        
                        print(f"[ALERTE SÉCURITÉ] {statut_final.upper()} détecté par {cam_name} ! Nom: {nom_final}")
                        last_capture_time = current_time
                        captured_this_frame = True
                        
        return frame, last_capture_time

    # --- Thread de la Caméra USB ---
    def process_usb_loop(self):
        while self.running:
            ret, frame = self.cap_usb.read()
            if ret:
                annotated_frame, new_time = self._process_frame_ai(
                    frame, "CAM-01", "Webcam USB", self.buffer_usb, self.last_capture_usb, self.face_detector_usb, self.face_recognizer_usb
                )
                self.last_capture_usb = new_time
                self.annotated_frame_usb = annotated_frame
            else:
                time.sleep(0.01)

    # --- Thread de la Caméra IP ---
    def process_ip_loop(self):
        while self.running:
            ret, frame = self.cap_ip.read()
            if ret:
                annotated_frame, new_time = self._process_frame_ai(
                    frame, "CAM-02", "Smartphone IP", self.buffer_ip, self.last_capture_ip, self.face_detector_ip, self.face_recognizer_ip
                )
                self.last_capture_ip = new_time
                self.annotated_frame_ip = annotated_frame
            else:
                time.sleep(0.01)

    # --- Affichage Synchronisé via Tkinter ---
    def update_video_labels(self):
        # Affichage USB
        if self.annotated_frame_usb is not None:
            f_usb = self.annotated_frame_usb.copy()
            f_rgb_usb = cv2.cvtColor(f_usb, cv2.COLOR_BGR2RGB)
            img_pil_usb = Image.fromarray(f_rgb_usb)
            # CTkImage corrige l'erreur "Image can not be scaled on HighDPI displays"
            img_ctk_usb = ctk.CTkImage(light_image=img_pil_usb, size=(480, 360))
            self.video_label_usb.configure(image=img_ctk_usb, text="")
            self.video_label_usb.image = img_ctk_usb

        # Affichage IP
        if self.annotated_frame_ip is not None:
            f_ip = self.annotated_frame_ip.copy()
            f_rgb_ip = cv2.cvtColor(f_ip, cv2.COLOR_BGR2RGB)
            img_pil_ip = Image.fromarray(f_rgb_ip)
            img_ctk_ip = ctk.CTkImage(light_image=img_pil_ip, size=(480, 360))
            self.video_label_ip.configure(image=img_ctk_ip, text="")
            self.video_label_ip.image = img_ctk_ip

        if self.running:
            self.after(30, self.update_video_labels)

    def on_close(self):
        self.running = False
        time.sleep(0.2)
        if self.cap_usb.isOpened(): self.cap_usb.release()
        if self.cap_ip.isOpened(): self.cap_ip.release()

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Système de Surveillance - Multithreading Double Caméra IA")
    root.geometry("1100x550")
    
    app = SmartSurveillanceApp(root)
    app.pack(fill="both", expand=True)
    
    def on_closing():
        app.on_close()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
