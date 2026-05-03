import cv2
import threading

class VideoStream:
    """
    Classe pour capturer le flux vidéo de la webcam dans un thread séparé.
    Permet d'améliorer les performances en ne bloquant pas le thread principal.
    """
    def __init__(self, src=0):
        # 1. Ouvrir la webcam ou la caméra réseau
        self.stream = cv2.VideoCapture(src)
        
        # Lire la première image pour s'assurer que le flux est bien ouvert
        # Les caméras IP sont souvent lentes à donner la première frame, on essaie plusieurs fois.
        import time
        for _ in range(30):
            self.grabbed, self.frame = self.stream.read()
            if self.grabbed:
                break
            time.sleep(0.02)
            
        # 1b. Fallback automatique si la caméra IP échoue
        if (not self.stream.isOpened() or not self.grabbed) and isinstance(src, str):
            print(f"❌ ERREUR : Flux {src} injoignable ou bloqué. Basculement d'urgence sur USB (0).")
            self.stream.release()
            self.stream = cv2.VideoCapture(0)
            self.grabbed, self.frame = self.stream.read()
            
        # Variable de contrôle pour indiquer l'arrêt du thread
        self.stopped = False
        
        # 2. Initialiser et démarrer le thread de lecture en continu
        self.thread = threading.Thread(target=self._update, args=())
        self.thread.daemon = True  # Le thread s'arrête avec le programme principal
        self.thread.start()

    def _update(self):
        """
        Méthode exécutée en arrière-plan par le thread.
        Elle met à jour l'image en continu depuis le flux vidéo.
        """
        while True:
            # Si on appelle la méthode stop(), on sort de la boucle
            if self.stopped:
                return
            
            # Sinon, on lit la prochaine image de la caméra
            (self.grabbed, self.frame) = self.stream.read()

    def get_frame(self):
        """
        3. Retourne la dernière image capturée de manière non bloquante.
        """
        return self.frame

    def stop(self):
        """
        4. Arrête le thread en toute sécurité et libère la ressource vidéo.
        """
        self.stopped = True
        
        # Attendre que le thread se termine proprement
        if self.thread.is_alive():
            self.thread.join()
            
        # Libérer l'objet VideoCapture de OpenCV
        self.stream.release()
