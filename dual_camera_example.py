import customtkinter as ctk
import cv2
import threading
from PIL import Image, ImageTk
import time

class DualCameraDashboard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 1. Interface : Zone avec deux labels vidéo côte à côte
        self.video_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.video_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configuration des colonnes pour un affichage symétrique
        self.video_frame.grid_columnconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(1, weight=1)
        
        # --- Caméra USB (Gauche) ---
        self.label_usb_title = ctk.CTkLabel(self.video_frame, text="Webcam USB (Locale)", font=("Helvetica", 16, "bold"), text_color="#3484F0")
        self.label_usb_title.grid(row=0, column=0, pady=(0, 10))
        self.video_label_usb = ctk.CTkLabel(self.video_frame, text="En attente du flux USB...", font=("Helvetica", 14), bg_color="#1E1E1E", width=480, height=360)
        self.video_label_usb.grid(row=1, column=0, padx=10)
        
        # --- Caméra IP (Droite) ---
        self.label_ip_title = ctk.CTkLabel(self.video_frame, text="Caméra IP (Réseau)", font=("Helvetica", 16, "bold"), text_color="#28A745")
        self.label_ip_title.grid(row=0, column=1, pady=(0, 10))
        self.video_label_ip = ctk.CTkLabel(self.video_frame, text="En attente du flux IP...", font=("Helvetica", 14), bg_color="#1E1E1E", width=480, height=360)
        self.video_label_ip.grid(row=1, column=1, padx=10)
        
        # 2. Initialisation des sources vidéo
        print("[INFO] Démarrage des caméras...")
        self.cap_usb = cv2.VideoCapture(0)
        self.cap_ip = cv2.VideoCapture("http://192.168.1.141:4747/video")
        
        # Variables partagées pour stocker les images
        self.frame_usb = None
        self.frame_ip = None
        self.running = True

        # 3. Multithreading : Création et lancement des Threads dédiés
        self.thread_usb = threading.Thread(target=self.capture_usb_loop, daemon=True)
        self.thread_ip = threading.Thread(target=self.capture_ip_loop, daemon=True)
        
        self.thread_usb.start()
        self.thread_ip.start()

        # 4. Lancement de la boucle d'affichage unifiée
        self.update_video_labels()

    # --- Thread dédié : Caméra USB ---
    def capture_usb_loop(self):
        while self.running:
            ret, frame = self.cap_usb.read()
            if ret:
                self.frame_usb = frame
            else:
                time.sleep(0.01) # Petite pause pour ne pas saturer le CPU si la caméra lag

    # --- Thread dédié : Caméra IP ---
    def capture_ip_loop(self):
        while self.running:
            ret, frame = self.cap_ip.read()
            if ret:
                self.frame_ip = frame
            else:
                time.sleep(0.01)

    # --- Méthode unifiée de mise à jour de l'interface ---
    def update_video_labels(self):
        # A. Conversion et affichage de la trame USB
        if self.frame_usb is not None:
            # On fait une copie pour éviter les conflits d'accès concurrentiel (Thread-safety)
            frame_u = self.frame_usb.copy()
            frame_rgb_u = cv2.cvtColor(frame_u, cv2.COLOR_BGR2RGB)
            img_u = Image.fromarray(frame_rgb_u).resize((480, 360))
            img_tk_u = ImageTk.PhotoImage(image=img_u)
            self.video_label_usb.configure(image=img_tk_u, text="")
            self.video_label_usb.image = img_tk_u

        # B. Conversion et affichage de la trame IP
        if self.frame_ip is not None:
            frame_i = self.frame_ip.copy()
            frame_rgb_i = cv2.cvtColor(frame_i, cv2.COLOR_BGR2RGB)
            img_i = Image.fromarray(frame_rgb_i).resize((480, 360))
            img_tk_i = ImageTk.PhotoImage(image=img_i)
            self.video_label_ip.configure(image=img_tk_i, text="")
            self.video_label_ip.image = img_tk_i

        # C. Boucle Tkinter : rappel de la méthode toutes les 30ms (~33 FPS)
        if self.running:
            self.after(30, self.update_video_labels)

    def on_close(self):
        """Méthode de nettoyage à appeler lors de la fermeture de l'application."""
        print("[INFO] Arrêt des flux vidéo...")
        self.running = False
        
        # Libération des ressources (Wait un peu pour que les threads s'arrêtent proprement)
        time.sleep(0.2)
        if self.cap_usb.isOpened():
            self.cap_usb.release()
        if self.cap_ip.isOpened():
            self.cap_ip.release()

if __name__ == "__main__":
    # Point d'entrée pour tester le module de double caméra de manière isolée
    root = ctk.CTk()
    root.title("Test - Double Caméra Side-by-Side")
    root.geometry("1050x500")
    
    app = DualCameraDashboard(root)
    app.pack(fill="both", expand=True)
    
    def on_closing():
        app.on_close()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
