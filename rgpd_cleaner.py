import sqlite3
import os
from datetime import datetime, timedelta

def run_rgpd_cleanup():
    """
    Script de maintenance visant à assurer la conformité avec le RGPD 
    (Règlement Général sur la Protection des Données).
    Purge toutes les données biométriques (images) et les métadonnées (logs) 
    qui ont dépassé la durée légale de conservation (30 jours).
    """
    print("=== Script de Nettoyage et Conformité RGPD ===")
    
    db_name = "surveillance.db"
    
    # Vérification de l'existence de la base
    if not os.path.exists(db_name):
        print("[INFO] La base de données 'surveillance.db' n'existe pas. Aucune purge nécessaire.")
        return
        
    # 2. Connexion à la base de données SQLite
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # 3. Calcul de la date limite de conservation
    # La fonction timedelta nous permet de reculer exactement de 30 jours
    date_limite = datetime.now() - timedelta(days=30)
    
    # On la formate en chaîne de caractères pour correspondre à notre table SQL (YYYY-MM-DD HH:MM:SS)
    date_limite_str = date_limite.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO] Seuil légal de conservation : tout ce qui est antérieur au {date_limite_str} sera détruit.")
    
    try:
        # 4. Requête SELECT pour cibler les données obsolètes
        # On sélectionne l'ID et le chemin de l'image pour les logs vieux de plus de 30 jours
        query_select = "SELECT id, image_path FROM logs WHERE timestamp < ?"
        cursor.execute(query_select, (date_limite_str,))
        obsolete_logs = cursor.fetchall()
        
        total_logs_to_delete = len(obsolete_logs)
        images_deleted_count = 0
        
        if total_logs_to_delete == 0:
            print("[INFO] Votre système est propre. Aucune donnée à purger aujourd'hui.")
        else:
            print(f"\n[ACTION] {total_logs_to_delete} événement(s) obsolète(s) détecté(s). Démarrage de la purge...")
            
            # 5. Destruction des preuves biométriques (images physiques)
            for row in obsolete_logs:
                log_id, image_path = row[0], row[1]
                
                # Vérifier si le chemin existe et n'est pas vide
                if image_path and os.path.exists(image_path):
                    try:
                        # Suppression physique du fichier image
                        os.remove(image_path)
                        images_deleted_count += 1
                    except Exception as e:
                        print(f"[ERREUR] Impossible de détruire le fichier '{image_path}' : {e}")
                else:
                    # Le fichier a peut-être déjà été supprimé manuellement, on l'indique simplement
                    pass 

            # 6. Purge définitive de la base de données
            # On efface les lignes de la table `logs` dont le timestamp est antérieur à la limite
            query_delete = "DELETE FROM logs WHERE timestamp < ?"
            cursor.execute(query_delete, (date_limite_str,))
            
            # Valider les modifications dans la BDD
            conn.commit()
            
            # 7. Bilan détaillé
            print(f"\n[SUCCÈS] Opération de conformité RGPD terminée.")
            print(f"  --> Preuves biométriques détruites : {images_deleted_count}")
            print(f"  --> Lignes SQL effacées            : {total_logs_to_delete}")
            
    except sqlite3.OperationalError as e:
        print(f"[ERREUR SQL] Impossible d'exécuter la requête : {e}")
    finally:
        # Toujours fermer la connexion
        conn.close()

if __name__ == "__main__":
    run_rgpd_cleanup()
