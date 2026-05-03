import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import sqlite3
import cv2
import os
import json
import numpy as np
import glob
from PIL import Image

# Imports nécessaires pour l'analytique visuelle (Data Science)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from db_manager import DBManager

# Importation du module de surveillance multicaméra IA Dynamique
from dynamic_surveillance import DynamicSurveillanceApp

# Configuration du thème global CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AdminDashboard:
    """
    Interface d'administration experte avec Temps Réel.
    Intègre désormais un rafraîchissement automatique non bloquant.
    """
    def __init__(self, root):
        # On instancie DBManager pour forcer la migration de la table (ex: ajout camera_name)
        DBManager()
        
        self.root = root
        self.root.title("Dashboard Administrateur - Sécurité & Analytique")
        self.root.geometry("1050x700")
        
        # Création du système d'onglets
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.tab_surveillance = self.tabview.add("Surveillance Directe")
        self.tab_hist = self.tabview.add("Historique")
        self.tab_stat = self.tabview.add("Statistiques")
        self.tab_config = self.tabview.add("Configuration")
        
        # Événement pour rafraîchir les graphiques quand on change d'onglet
        self.tabview.configure(command=self.on_tab_change)

        # Variables pour garder la trace des anciens graphiques et les détruire
        self.pie_canvas = None
        self.bar_canvas = None

        # Construction des interfaces des quatre onglets
        self.setup_surveillance_tab()
        self.setup_historique_tab()
        self.setup_statistiques_tab()
        self.setup_config_tab()
        
        # 6. Démarrage de la boucle de rafraîchissement en temps réel
        self.auto_refresh()

    def on_tab_change(self):
        """Met à jour les graphiques lorsqu'on passe sur l'onglet Statistiques."""
        if self.tabview.get() == "Statistiques":
            self.draw_charts()

    # ==========================================
    # === SYSTÈME DE TEMPS RÉEL (AUTO REFRESH)
    # ==========================================
    def auto_refresh(self):
        """
        1 & 2 & 3. Rafraîchit automatiquement le tableau et les graphiques toutes les 2 secondes.
        Prend en compte le filtre actuellement sélectionné.
        """
        # Recharge les données dans le tableau selon le filtre
        self.load_data()
        
        # 4. Met à jour les graphiques
        # (Petite optimisation : on ne redessine les graphiques que si l'onglet Statistiques est ouvert
        # pour économiser énormément de mémoire et de CPU).
        if self.tabview.get() == "Statistiques":
            self.draw_charts()
            
        # 5. Boucle infinie non bloquante (2000 millisecondes = 2 secondes)
        self.root.after(2000, self.auto_refresh)

    # ==========================================
    # === ONGLET 0 : SURVEILLANCE EN DIRECT ===
    # ==========================================
    def setup_surveillance_tab(self):
        # On instancie la NOUVELLE application dynamique de surveillance
        self.surveillance_app = DynamicSurveillanceApp(self.tab_surveillance)
        self.surveillance_app.pack(fill="both", expand=True)

    # ==========================================
    # === ONGLET 1 : HISTORIQUE ET RECHERCHE ===
    # ==========================================
    def setup_historique_tab(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=30,
                        fieldbackground="#2b2b2b", bordercolor="#343638", borderwidth=0, font=('Helvetica', 11))
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white",
                        relief="flat", font=('Helvetica', 12, 'bold'))
        style.map("Treeview.Heading", background=[('active', '#3484F0')])

        # --- BARRE D'OUTILS DE FILTRAGE (RECHERCHE AVANCÉE) ---
        search_frame = ctk.CTkFrame(self.tab_hist)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 1. Filtre Source
        ctk.CTkLabel(search_frame, text="Source :", font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=(10, 5), pady=10)
        self.source_filter_var = ctk.StringVar(value="Toutes")
        self.source_menu = ctk.CTkOptionMenu(
            search_frame, variable=self.source_filter_var,
            values=["Toutes", "Caméra USB", "Caméra IP"],
            font=("Helvetica", 12), width=150
        )
        self.source_menu.pack(side=tk.LEFT, padx=5)
        
        # 2. Filtre Plage Horaire
        ctk.CTkLabel(search_frame, text="De :", font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.time_start_entry = ctk.CTkEntry(search_frame, placeholder_text="00:00", width=60, font=("Helvetica", 12))
        self.time_start_entry.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(search_frame, text="À :", font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=(5, 5))
        self.time_end_entry = ctk.CTkEntry(search_frame, placeholder_text="23:59", width=60, font=("Helvetica", 12))
        self.time_end_entry.pack(side=tk.LEFT, padx=5)
        
        # 3. Filtre Statut (Réintégré)
        ctk.CTkLabel(search_frame, text="Statut :", font=("Helvetica", 13, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.filter_var = ctk.StringVar(value="Tous")
        self.status_menu = ctk.CTkOptionMenu(
            search_frame, variable=self.filter_var,
            values=["Tous", "autorisé", "non autorisé", "inconnu"],
            font=("Helvetica", 12), width=120
        )
        self.status_menu.pack(side=tk.LEFT, padx=5)
        
        # 4. Bouton Appliquer
        filter_btn = ctk.CTkButton(
            search_frame, text="🔍 Appliquer le filtre", command=self.apply_filter,
            font=("Helvetica", 12, "bold"), fg_color="#3484F0"
        )
        filter_btn.pack(side=tk.LEFT, padx=20)

        # --- SECTION TABLEAU DES LOGS ---
        columns = ("ID", "Date/Heure", "ID Caméra", "Nom Caméra", "Statut")
        self.tree = ttk.Treeview(self.tab_hist, columns=columns, show="headings")
        
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=60, anchor=tk.CENTER)
        self.tree.heading("Date/Heure", text="Date/Heure")
        self.tree.column("Date/Heure", width=220, anchor=tk.CENTER)
        self.tree.heading("ID Caméra", text="ID Caméra")
        self.tree.column("ID Caméra", width=100, anchor=tk.CENTER)
        self.tree.heading("Nom Caméra", text="Nom Caméra")
        self.tree.column("Nom Caméra", width=150, anchor=tk.CENTER)
        self.tree.heading("Statut", text="Statut")
        self.tree.column("Statut", width=120, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self.tab_hist, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.tree.tag_configure('alerte', foreground='#ff6b6b')
        self.tree.tag_configure('autorise', foreground='#51cf66')
        self.tree.bind("<Double-1>", self.on_double_click)

    # ==========================================
    # === ONGLET 4 : CONFIGURATION ÉPURÉE    ===
    # ==========================================
    def setup_config_tab(self):
        # 1. Ajout Rapide de Caméra IP
        cam_frame = ctk.CTkFrame(self.tab_config)
        cam_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(cam_frame, text="Ajout Rapide de Caméra IP", font=("Helvetica", 16, "bold")).pack(pady=(15, 5))
        
        input_frame = ctk.CTkFrame(cam_frame, fg_color="transparent")
        input_frame.pack(pady=10)
        
        ctk.CTkLabel(input_frame, text="Adresse IP :", font=("Helvetica", 13)).pack(side="left", padx=5)
        self.ip_entry = ctk.CTkEntry(input_frame, placeholder_text="192.168.1.15", width=130)
        self.ip_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(input_frame, text="Port :", font=("Helvetica", 13)).pack(side="left", padx=(15, 5))
        self.port_entry = ctk.CTkEntry(input_frame, placeholder_text="4747", width=70)
        self.port_entry.pack(side="left", padx=5)
        
        def on_add_ip_cam():
            ip = self.ip_entry.get().strip()
            port = self.port_entry.get().strip()
            if ip and port:
                url = f"http://{ip}:{port}/video"
                name = f"Caméra IP ({ip})"
                # Si le module DynamicSurveillance est chargé, on y injecte la caméra
                if hasattr(self, 'surveillance_app'):
                    self.surveillance_app.add_camera(name, url)
                    messagebox.showinfo("Succès", f"La {name} a été connectée au système.")
                else:
                    messagebox.showwarning("Erreur", "Le module de Surveillance Directe n'est pas prêt.")
            else:
                messagebox.showerror("Erreur", "Veuillez remplir l'IP et le Port.")
                
        ctk.CTkButton(cam_frame, text="🔌 Connecter au réseau", command=on_add_ip_cam, font=("Helvetica", 13, "bold")).pack(pady=(5, 15))

        # 2. Gestion des Utilisateurs (Déplacée ici)
        user_frame = ctk.CTkFrame(self.tab_config)
        user_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(user_frame, text="Gestion des Accès", font=("Helvetica", 16, "bold")).pack(pady=(15, 5))
        
        btn_frame = ctk.CTkFrame(user_frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        ctk.CTkButton(btn_frame, text="➕ Ajouter un Utilisateur", command=self.open_add_user_window, 
                      font=("Helvetica", 13, "bold"), fg_color="#28a745", hover_color="#218838").pack(side="left", padx=15)
                      
        ctk.CTkButton(btn_frame, text="🗑️ Supprimer un Utilisateur", command=self.open_delete_user_window, 
                      font=("Helvetica", 13, "bold"), fg_color="#dc3545", hover_color="#c82333").pack(side="left", padx=15)

    def apply_filter(self):
        """Action manuelle déclenchée par les boutons (effectue un rafraîchissement immédiat)."""
        self.load_data()
        if self.tabview.get() == "Statistiques":
            self.draw_charts()

    def load_data(self):
        """Logique de filtrage SQL Avancée pour l'onglet Historique."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        db_path = "surveillance.db"
        if not os.path.exists(db_path):
            return

        # Récupération des filtres
        source_val = getattr(self, 'source_filter_var', ctk.StringVar(value="Toutes")).get()
        t_start = getattr(self, 'time_start_entry', None)
        t_start_val = t_start.get().strip() if t_start else ""
        t_end = getattr(self, 'time_end_entry', None)
        t_end_val = t_end.get().strip() if t_end else ""

        if not t_start_val: t_start_val = "00:00"
        if not t_end_val: t_end_val = "23:59"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Requête SQL Dynamique
            query = "SELECT id, timestamp, camera_id, camera_name, status FROM logs WHERE strftime('%H:%M', timestamp) BETWEEN ? AND ?"
            params = [t_start_val, t_end_val]
            
            # Filtre Statut
            status_val = getattr(self, 'filter_var', ctk.StringVar(value="Tous")).get()
            if status_val != "Tous":
                query += " AND status = ?"
                params.append(status_val)
            
            # Filtre Source
            if source_val == "Caméra USB":
                query += " AND camera_name NOT LIKE '%IP%'"
            elif source_val == "Caméra IP":
                query += " AND camera_name LIKE '%IP%'"
                
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            for row in rows:
                log_id, timestamp, camera_id, camera_name, status = row
                if camera_name is None:
                    camera_name = "Inconnu"
                    
                row_tag = 'alerte' if status in ("non autorisé", "inconnu") else 'autorise'
                self.tree.insert("", tk.END, values=(log_id, timestamp, camera_id, camera_name, status), tags=(row_tag,))
                
            conn.close()
        except sqlite3.Error as e:
            print(f"Erreur SQL: {e}")

    def on_double_click(self, event):
        """Ouvre l'image de la preuve stockée (forensique)."""
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        item = selected_item[0]
        log_id = self.tree.item(item, "values")[0]

        conn = sqlite3.connect("surveillance.db")
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM logs WHERE id=?", (log_id,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            image_path = result[0]
            if os.path.exists(image_path):
                image = cv2.imread(image_path)
                window_title = f"Preuve Forensique - Log #{log_id}"
                cv2.imshow(window_title, image)
                cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 1)
            else:
                messagebox.showwarning("Preuve introuvable", "Le fichier physique de l'image a été supprimé.")

    # ==========================================
    # === ONGLET 2 : STATISTIQUES (MATPLOTLIB)
    # ==========================================
    def setup_statistiques_tab(self):
        """Prépare la structure pour accueillir les graphiques."""
        self.frame_pie = ctk.CTkFrame(self.tab_stat)
        self.frame_pie.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.frame_bar = ctk.CTkFrame(self.tab_stat)
        self.frame_bar.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    def draw_charts(self):
        """Génère ou met à jour les graphiques Matplotlib."""
        db_path = "surveillance.db"
        if not os.path.exists(db_path):
            return

        # 4. IMPORTANT : Nettoyage strict des anciens Canvas
        if self.pie_canvas:
            self.pie_canvas.get_tk_widget().destroy()
        if self.bar_canvas:
            self.bar_canvas.get_tk_widget().destroy()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        bg_color = '#2b2b2b'
        text_color = '#e0e0e0'
        
        # ------------------------------------------
        # GRAPHIQUE 1 : Camembert (Pie Chart global)
        # ------------------------------------------
        cursor.execute("SELECT status, COUNT(*) FROM logs GROUP BY status")
        pie_data = cursor.fetchall()
        
        labels = []
        sizes = []
        colors = []
        color_map = {'autorisé': '#51cf66', 'non autorisé': '#ff6b6b', 'inconnu': '#fcc419'}
        
        for status, count in pie_data:
            labels.append(status.capitalize())
            sizes.append(count)
            colors.append(color_map.get(status.lower(), '#339af0'))

        fig_pie, ax_pie = plt.subplots(figsize=(4, 4), dpi=100)
        fig_pie.patch.set_facecolor(bg_color)
        ax_pie.set_facecolor(bg_color)
        
        if sizes:
            ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                       startangle=140, textprops={'color': text_color, 'fontweight': 'bold'})
            ax_pie.set_title("Répartition Globale des Détections", color=text_color, pad=20, fontweight='bold')
        else:
            ax_pie.text(0.5, 0.5, "Aucune donnée", ha='center', va='center', color=text_color)
            ax_pie.axis('off')

        self.pie_canvas = FigureCanvasTkAgg(fig_pie, master=self.frame_pie)
        self.pie_canvas.draw()
        self.pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ------------------------------------------
        # GRAPHIQUE 2 : Bar Chart (Heures de pointe)
        # ------------------------------------------
        status_filter = self.filter_var.get()
        
        if status_filter == "Tous":
            cursor.execute("SELECT timestamp FROM logs")
        else:
            cursor.execute("SELECT timestamp FROM logs WHERE status = ?", (status_filter,))
            
        bar_data = cursor.fetchall()
        conn.close()

        hours_count = {f"{i:02d}": 0 for i in range(24)}
        for row in bar_data:
            ts = row[0]
            try:
                hour = ts.split(" ")[1].split(":")[0]
                hours_count[hour] += 1
            except IndexError:
                continue
                
        hours = list(hours_count.keys())
        counts = list(hours_count.values())

        fig_bar, ax_bar = plt.subplots(figsize=(5, 4), dpi=100)
        fig_bar.patch.set_facecolor(bg_color)
        ax_bar.set_facecolor(bg_color)
        
        ax_bar.spines['bottom'].set_color(text_color)
        ax_bar.spines['left'].set_color(text_color)
        ax_bar.spines['top'].set_visible(False)
        ax_bar.spines['right'].set_visible(False)
        ax_bar.tick_params(axis='x', colors=text_color)
        ax_bar.tick_params(axis='y', colors=text_color)

        bar_color = '#3484F0'
        ax_bar.bar(hours, counts, color=bar_color)
        
        plt.setp(ax_bar.get_xticklabels(), rotation=45, ha="right")
        
        filter_title = f"(Filtre : {status_filter})"
        ax_bar.set_title(f"Heures de Pointe\n{filter_title}", color=text_color, pad=15, fontweight='bold')
        ax_bar.set_ylabel("Nombre de détections", color=text_color)

        self.bar_canvas = FigureCanvasTkAgg(fig_bar, master=self.frame_bar)
        self.bar_canvas.draw()
        self.bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        plt.close(fig_pie)
        plt.close(fig_bar)

    # ==========================================
    # === MOTEUR IA : FONCTION RÉUTILISABLE  ===
    # ==========================================
    def _retrain_ai_model(self):
        dataset_dir = "dataset"
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir)
            
        image_paths = [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir) if f.endswith('.jpg')]
        
        if not image_paths:
            if os.path.exists("trainer.yml"):
                os.remove("trainer.yml")
            return True, "Aucune donnée restante. Le modèle IA a été réinitialisé."

        faces_list = []
        ids_list = []

        for image_path in image_paths:
            pil_image = Image.open(image_path).convert('L')
            image_np = np.array(pil_image, 'uint8')
            
            filename = os.path.split(image_path)[-1]
            try:
                user_id = int(filename.split(".")[1])
                faces_list.append(image_np)
                ids_list.append(user_id)
            except (IndexError, ValueError):
                continue

        if faces_list and ids_list:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.train(faces_list, np.array(ids_list))
            recognizer.write('trainer.yml')
            return True, "Le modèle IA a été ré-entraîné avec succès."
        else:
            if os.path.exists("trainer.yml"):
                os.remove("trainer.yml")
            return False, "Les données trouvées sont invalides. Modèle réinitialisé."

    # ==========================================
    # === SYSTÈME D'ENRÔLEMENT (AJOUT USER)  ===
    # ==========================================
    def open_add_user_window(self):
        self.add_window = ctk.CTkToplevel(self.root)
        self.add_window.title("Enrôler un Nouvel Utilisateur")
        self.add_window.geometry("450x450")
        self.add_window.grab_set()

        ctk.CTkLabel(self.add_window, text="Nom et Prénom :", font=("Helvetica", 14, "bold")).pack(pady=(20, 5))
        self.entry_nom = ctk.CTkEntry(self.add_window, font=("Helvetica", 13), width=300)
        self.entry_nom.pack(pady=5)

        ctk.CTkLabel(self.add_window, text="Numéro de CIN :", font=("Helvetica", 14, "bold")).pack(pady=(10, 5))
        self.entry_cin = ctk.CTkEntry(self.add_window, font=("Helvetica", 13), width=300)
        self.entry_cin.pack(pady=5)

        ctk.CTkLabel(self.add_window, text="Statut d'accès :", font=("Helvetica", 14, "bold")).pack(pady=(10, 5))
        self.status_var_add = ctk.StringVar(value="autorisé")
        self.entry_status = ctk.CTkOptionMenu(
            self.add_window, variable=self.status_var_add, 
            values=["autorisé", "non autorisé"], font=("Helvetica", 13), width=300
        )
        self.entry_status.pack(pady=5)

        self.info_label = ctk.CTkLabel(self.add_window, text="", font=("Helvetica", 12, "italic"), text_color="#3484F0")
        self.info_label.pack(pady=15)

        start_btn = ctk.CTkButton(
            self.add_window, text="📸 Démarrer l'enregistrement", 
            command=self.start_capture_and_train, 
            font=("Helvetica", 13, "bold")
        )
        start_btn.pack(pady=10)

    def start_capture_and_train(self):
        nom = self.entry_nom.get().strip()
        cin = self.entry_cin.get().strip()
        statut_choisi = self.status_var_add.get()

        if not nom or not cin:
            messagebox.showerror("Erreur de saisie", "Veuillez remplir le Nom et le CIN.", parent=self.add_window)
            return

        json_path = "users.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    users_data = json.load(f)
            except json.JSONDecodeError:
                users_data = {}
        else:
            users_data = {}

        self.new_id = max(int(k) for k in users_data.keys()) + 1 if users_data else 1
        self.current_nom = nom
        users_data[str(self.new_id)] = {"nom": nom, "cin": cin, "statut": statut_choisi}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)

        self.dataset_dir = "dataset"
        if not os.path.exists(self.dataset_dir):
            os.makedirs(self.dataset_dir)

        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_detector = cv2.CascadeClassifier(cascade_path)

        self.info_label.configure(text="Capture en cours... Regardez la caméra.")
        
        # Agrandir légèrement la fenêtre pour accommoder la vidéo
        self.add_window.geometry("550x650")
        self.video_label = ctk.CTkLabel(self.add_window, text="")
        self.video_label.pack(pady=10)

        # LECTURE DE LA CONFIGURATION
        camera_source = 0
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    conf = json.load(f)
                    mode = conf.get("mode", "usb")
                    legacy_source = conf.get("camera_source", "")
                    if mode == "ip":
                        ip = conf.get("ip", "")
                        port = conf.get("port", "")
                        if ip and port:
                            camera_source = f"http://{ip}:{port}/video"
                    elif legacy_source and legacy_source != "0":
                        camera_source = legacy_source
            except Exception:
                pass

        self.cap = cv2.VideoCapture(camera_source)
        if isinstance(camera_source, str) and not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            
        self.capture_count = 0
        self.retry_count = 0
        self.update_capture_frame()

    def update_capture_frame(self):
        from PIL import ImageTk
        
        ret, frame = self.cap.read()
        if not ret:
            self.retry_count += 1
            if self.retry_count < 30:
                # Retenter 30 fois (~600ms) car les flux IP peuvent être capricieux au démarrage
                self.add_window.after(20, self.update_capture_frame)
                return
                
            messagebox.showerror(
                "Erreur Caméra", 
                "Impossible d'accéder à la caméra.\n\n⚠️ IMPORTANT : Si 'main.py' est en cours d'exécution en arrière-plan, il bloque l'accès à la caméra. Veuillez le fermer avant d'ajouter un utilisateur.", 
                parent=self.add_window
            )
            self.cap.release()
            self.add_window.destroy()
            return
            
        self.retry_count = 0  # Reset si on a réussi à lire

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            self.capture_count += 1
            face_roi = gray[y:y+h, x:x+w]
            
            file_path = os.path.join(self.dataset_dir, f"User.{self.new_id}.{self.capture_count}.jpg")
            cv2.imwrite(file_path, face_roi)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            break 

        # Conversion OpenCV BGR -> RGB -> PIL -> ImageTk
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)
        img_pil = img_pil.resize((450, 337))  # Resize 4:3 standard
        img_tk = ImageTk.PhotoImage(image=img_pil)
        
        self.video_label.configure(image=img_tk, text="")
        self.video_label.image = img_tk  # Garbage collection protection

        if self.capture_count >= 50:
            self.cap.release()
            self.video_label.destroy()
            self.info_label.configure(text="Entraînement de l'IA en cours, veuillez patienter...", text_color="#FF9800")
            self.add_window.update()

            success, msg = self._retrain_ai_model()
            
            self.info_label.configure(text="")
            if success:
                messagebox.showinfo("Enrôlement Terminé", f"L'utilisateur {self.current_nom} a été ajouté.\n{msg}", parent=self.add_window)
                self.add_window.destroy()
            else:
                messagebox.showerror("Erreur", msg, parent=self.add_window)
        else:
            self.info_label.configure(text=f"Capture en cours... {self.capture_count}/50")
            # 4. Boucle récursive non bloquante
            self.add_window.after(20, self.update_capture_frame)

    # ==========================================
    # === SYSTÈME DE SUPPRESSION D'USER      ===
    # ==========================================
    def open_delete_user_window(self):
        self.del_window = ctk.CTkToplevel(self.root)
        self.del_window.title("Supprimer un utilisateur")
        self.del_window.geometry("450x250")
        self.del_window.grab_set()
        
        json_path = "users.json"
        self.users_data_cache = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.users_data_cache = json.load(f)
            except json.JSONDecodeError:
                pass
                
        user_list = []
        for uid, info in self.users_data_cache.items():
            user_list.append(f"{uid} - {info.get('nom', 'Inconnu')} ({info.get('cin', 'N/A')})")
            
        if not user_list:
            messagebox.showinfo("Vide", "Aucun utilisateur présent dans la base de données JSON.", parent=self.del_window)
            self.del_window.destroy()
            return

        ctk.CTkLabel(self.del_window, text="Sélectionnez l'utilisateur à purger :", font=("Helvetica", 14, "bold")).pack(pady=(20, 10))
        
        self.combo_users = ctk.CTkComboBox(self.del_window, values=user_list, font=("Helvetica", 13), width=300, state="readonly")
        self.combo_users.pack(pady=10)
        self.combo_users.set(user_list[0])
        
        self.del_info_label = ctk.CTkLabel(self.del_window, text="", font=("Helvetica", 12, "italic"), text_color="#ff6b6b")
        self.del_info_label.pack(pady=5)
        
        del_btn = ctk.CTkButton(
            self.del_window, text="🗑️ Confirmer la suppression", 
            command=self.confirm_delete_user, 
            font=("Helvetica", 13, "bold"), fg_color="#dc3545", hover_color="#c82333"
        )
        del_btn.pack(pady=10)

    def confirm_delete_user(self):
        selection = self.combo_users.get()
        if not selection:
            return
            
        user_id_str = selection.split(" - ")[0]
        
        self.del_info_label.configure(text="Nettoyage des données en cours...")
        self.del_window.update()
        
        if user_id_str in self.users_data_cache:
            del self.users_data_cache[user_id_str]
            with open("users.json", "w", encoding="utf-8") as f:
                json.dump(self.users_data_cache, f, indent=4, ensure_ascii=False)
                
        dataset_dir = "dataset"
        images_to_delete = glob.glob(os.path.join(dataset_dir, f"User.{user_id_str}.*.jpg"))
        
        count_deleted = 0
        for img_path in images_to_delete:
            try:
                os.remove(img_path)
                count_deleted += 1
            except Exception as e:
                print(f"[ERREUR] Impossible de supprimer {img_path} : {e}")
                
        self.del_info_label.configure(text="Réentraînement de l'IA (mise à jour du cerveau)...")
        self.del_window.update()
        
        success, msg = self._retrain_ai_model()
        
        self.del_info_label.configure(text="")
        if success:
            messagebox.showinfo(
                "Suppression validée", 
                f"L'utilisateur a été effacé du système.\n"
                f"- {count_deleted} images biométriques détruites.\n"
                f"- {msg}", 
                parent=self.del_window
            )
        else:
            messagebox.showwarning("Informations de suppression", msg, parent=self.del_window)
            
        self.del_window.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = AdminDashboard(root)
    
    def on_closing():
        # S'assure que les threads de la caméra sont arrêtés proprement
        if hasattr(app, 'surveillance_app'):
            app.surveillance_app.on_close()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
