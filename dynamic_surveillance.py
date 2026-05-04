import customtkinter as ctk
import cv2
import threading
import time
import os
import datetime
import uuid
from collections import Counter
from PIL import Image

# Importation des modules existants de votre projet
from face_detector import FaceDetector
from face_recognizer import FaceRecognizer
from db_manager import DBManager
from watermarker import Watermarker
from telegram_alert import send_telegram_alert

TELEGRAM_TOKEN = "VOTRE_TOKEN_TELEGRAM"
TELEGRAM_CHAT_ID = "VOTRE_CHAT_ID"

class CameraWorker(threading.Thread):
    """
    Un Thread totalement autonome qui gère une caméra, sa connexion OpenCV, 
    et toute son intelligence artificielle (Haar Cascade + LBPH).
    """
    def __init__(self, cam_id, cam_name, source_url):
        super().__init__(daemon=True)
        self.cam_id = cam_id
        self.cam_name = cam_name
        self.source_url = source_url
        
        # Outils indépendants (Thread-Safe en RAM)
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.db_manager = DBManager()
        self.watermarker = Watermarker(alpha=0.1)
        self.captures_dir = "captures"
        
        self.buffer = []
        self.last_capture = 0
        
        # --- Variables Anti-Spam (Telegram) ---
        self.last_alert_time = 0
        self.alert_cooldown = 15  # 15 secondes d'attente entre deux alertes pour cette caméra
        
        self.cap = None
        self.running = True
        self.annotated_frame = None
        self.is_connected = False
        self.should_pause = False

    def run(self):
        while self.running:
            if self.should_pause:
                if self.is_connected:
                    self.is_connected = False
                    if self.cap and self.cap.isOpened():
                        self.cap.release()
                time.sleep(0.5)
                continue

            if not self.is_connected:
                source = int(self.source_url) if str(self.source_url).isdigit() else self.source_url
                try:
                    self.cap = cv2.VideoCapture(source)
                    self.is_connected = self.cap.isOpened()
                except Exception:
                    self.is_connected = False
                if not self.is_connected:
                    time.sleep(1)
                continue
                
            ret, frame = self.cap.read()
            if ret:
                self.annotated_frame, self.last_capture = self._process_frame_ai(frame)
            else:
                self.is_connected = False
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                time.sleep(0.1)
                
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def pause(self):
        """Libère temporairement la caméra (ex: pour l'ajout d'un utilisateur)."""
        self.should_pause = True
            
    def resume(self):
        """Reconnecte la caméra après une pause."""
        self.face_recognizer = FaceRecognizer() # Recharge le modèle après l'ajout d'un user
        self.should_pause = False

    def _process_frame_ai(self, frame):
        clean_frame = frame.copy()
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_detector.detect(frame)
        if len(faces) == 0:
            self.buffer.clear()
            return frame, self.last_capture
            
        captured_this_frame = False
        current_time = time.time()
        
        for (x, y, w, h) in faces:
            face_roi = gray_frame[y:y+h, x:x+w]
            nom_brut, statut_brut, confiance = self.face_recognizer.identify(face_roi)
            self.buffer.append((nom_brut, statut_brut))
            
            if len(self.buffer) > 20:
                self.buffer.pop(0)
                
            if len(self.buffer) < 20:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
                cv2.putText(frame, "Analyse...", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            else:
                noms = [item[0] for item in self.buffer]
                statuts = [item[1] for item in self.buffer]
                nom_final = Counter(noms).most_common(1)[0][0]
                statut_final = Counter(statuts).most_common(1)[0][0]
                
                color = (0, 255, 0) if statut_final == "autorisé" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{nom_final} ({statut_final})", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                if not captured_this_frame and (current_time - self.last_capture > 5):
                    if statut_final in ["non autorisé", "inconnu"]:
                        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        img_path = os.path.join(self.captures_dir, f"log_{self.cam_id}_{now_str}.jpg")
                        
                        watermarked_img = self.watermarker.apply_dct_watermark(clean_frame, f"{now_str} {self.cam_name}")
                        cv2.imwrite(img_path, watermarked_img if watermarked_img is not None else clean_frame)
                        
                        self.db_manager.log_event(self.cam_id, statut_final, img_path, camera_name=self.cam_name)
                        
                        # --- Logique Anti-Spam Telegram ---
                        if current_time - self.last_alert_time > self.alert_cooldown:
                            threading.Thread(
                                target=send_telegram_alert, 
                                args=(img_path, nom_final, statut_final, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID), 
                                daemon=True
                            ).start()
                            self.last_alert_time = current_time
                        
                        self.last_capture = current_time
                        captured_this_frame = True
                        
        return frame, self.last_capture

    def stop(self):
        self.running = False


class DynamicSurveillanceApp(ctk.CTkFrame):
    """
    Interface Dashboard Ultra-Moderne permettant l'ajout dynamique de caméras.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.workers = {}
        self.ui_elements = {}
        
        # --- Top Control Panel ---
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.pack(fill="x", padx=20, pady=10)
        
        self.title_lbl = ctk.CTkLabel(self.top_panel, text="Réseau de Caméras Actives", font=("Helvetica", 22, "bold"))
        self.title_lbl.pack(side="left")
        
        self.add_btn = ctk.CTkButton(self.top_panel, text="➕ Ajouter une Caméra", 
                                     font=("Helvetica", 14, "bold"), fg_color="#28a745", 
                                     hover_color="#218838", command=self.open_add_camera_dialog)
        self.add_btn.pack(side="right")
        
        # --- Scrollable Grid (Glassmorphism look) ---
        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.running = True
        
        # Ajout direct de la webcam par défaut (optionnel, pour l'UX)
        self.add_camera("Webcam Principale", "0")
        
        self.update_video_labels()

    def open_add_camera_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Ajouter une Caméra")
        dialog.geometry("450x450")
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text="Ajout Dynamique de Source", font=("Helvetica", 18, "bold")).pack(pady=(20, 10))
        
        ctk.CTkLabel(dialog, text="Nom de la Caméra :", font=("Helvetica", 14)).pack(pady=(5, 5))
        name_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="Ex: Parking Sud")
        name_entry.pack(pady=5)
        
        # --- Séparation propre avec des Onglets ---
        tabview = ctk.CTkTabview(dialog, width=350, height=180)
        tabview.pack(padx=20, pady=10)
        
        tab_ip = tabview.add("Caméra IP (Réseau)")
        tab_usb = tabview.add("Webcam USB (Locale)")
        
        # Tab IP
        ip_frame = ctk.CTkFrame(tab_ip, fg_color="transparent")
        ip_frame.pack(pady=20)
        ctk.CTkLabel(ip_frame, text="IP :", font=("Helvetica", 13)).pack(side="left", padx=5)
        ip_entry = ctk.CTkEntry(ip_frame, width=130, placeholder_text="192.168.1.15")
        ip_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(ip_frame, text="Port :", font=("Helvetica", 13)).pack(side="left", padx=(15, 5))
        port_entry = ctk.CTkEntry(ip_frame, width=70, placeholder_text="4747")
        port_entry.pack(side="left", padx=5)
        
        # Tab USB
        ctk.CTkLabel(tab_usb, text="Index matériel de la Webcam :", font=("Helvetica", 13)).pack(pady=(20, 5))
        usb_entry = ctk.CTkEntry(tab_usb, width=100, placeholder_text="0")
        usb_entry.pack(pady=5)
        
        def confirm():
            name = name_entry.get().strip()
            if not name:
                return
                
            active_tab = tabview.get()
            if active_tab == "Caméra IP (Réseau)":
                ip = ip_entry.get().strip()
                port = port_entry.get().strip()
                if ip and port:
                    source = f"http://{ip}:{port}/video"
                    self.add_camera(name, source)
                    dialog.destroy()
            else:
                idx = usb_entry.get().strip()
                source = idx if idx else "0"
                self.add_camera(name, source)
                dialog.destroy()
                
        ctk.CTkButton(dialog, text="Connecter la Caméra", command=confirm, font=("Helvetica", 14, "bold"), fg_color="#3484F0", height=40).pack(pady=(10, 20))

    def add_camera(self, name, source):
        # Identifiant unique sécurisé
        cam_id = str(uuid.uuid4())[:8]
        
        # Création de la Carte UI ("Card")
        card = ctk.CTkFrame(self.grid_frame, corner_radius=10, fg_color="#1a1a1a")
        
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)
        
        # Header de la Carte (Titre + Bouton Delete)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=8)
        
        status_dot = ctk.CTkLabel(header, text="🟢", font=("Helvetica", 12))
        status_dot.pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(header, text=name.upper(), font=("Helvetica", 14, "bold"), text_color="#e0e0e0").pack(side="left")
        
        def remove_cmd():
            self.remove_camera(cam_id)
            
        del_btn = ctk.CTkButton(header, text="✖", width=28, height=28, fg_color="#dc3545", hover_color="#c82333", command=remove_cmd)
        del_btn.pack(side="right")
        
        # Zone Vidéo
        vid_lbl = ctk.CTkLabel(card, text="🔌 Connexion en cours...", width=400, height=300, bg_color="#0d0d0d", font=("Helvetica", 12, "italic"))
        vid_lbl.pack(padx=10, pady=(0, 10))
        
        # Création et lancement du Thread en arrière-plan
        worker = CameraWorker(cam_id, name, source)
        worker.start()
        
        self.workers[cam_id] = worker
        self.ui_elements[cam_id] = {"card": card, "label": vid_lbl, "status": status_dot}
        
        self._repack_grid()

    def remove_camera(self, cam_id):
        if cam_id in self.workers:
            self.workers[cam_id].stop()
            del self.workers[cam_id]
        if cam_id in self.ui_elements:
            self.ui_elements[cam_id]["card"].destroy()
            del self.ui_elements[cam_id]
        self._repack_grid()

    def _repack_grid(self):
        # Réorganise la grille proprement (2 colonnes dynamiques)
        for i, (cid, elements) in enumerate(self.ui_elements.items()):
            row = i // 2
            col = i % 2
            elements["card"].grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

    def update_video_labels(self):
        if not self.running:
            return
            
        # Chef d'orchestre : Récupère les frames de toutes les caméras actives
        for cam_id, worker in list(self.workers.items()):
            if cam_id in self.ui_elements:
                lbl = self.ui_elements[cam_id]["label"]
                dot = self.ui_elements[cam_id]["status"]
                
                if worker.annotated_frame is not None:
                    dot.configure(text="🟢")
                    f = worker.annotated_frame.copy()
                    f_rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(f_rgb)
                    img_ctk = ctk.CTkImage(light_image=img_pil, size=(400, 300))
                    lbl.configure(image=img_ctk, text="")
                    lbl.image = img_ctk
                elif not worker.is_connected:
                    dot.configure(text="🔴")
                    lbl.configure(text="❌ Flux indisponible / Déconnecté")
                    
        self.after(30, self.update_video_labels)

    def on_close(self):
        self.running = False
        for worker in self.workers.values():
            worker.stop()

    def pause_all(self):
        for worker in self.workers.values():
            worker.pause()
            
    def resume_all(self):
        for worker in self.workers.values():
            worker.resume()
