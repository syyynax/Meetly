import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timedelta, time
import os

# --- MACHINE LEARNING ERKLÄRUNG FÜR DIE BEWERTUNG ---
# Wir nutzen hier keinen externen KI-Dienst (kein API-Aufruf).
# Stattdessen implementieren wir einen "Content-Based Recommender" Algorithmus.
# Funktionsweise:
# 1. Feature Engineering: Wir kombinieren Titel, Kategorie und Beschreibung zu einem Text-Vektor.
# 2. TF-IDF Vektorisierung: Wir wandeln diesen Text in mathematische Vektoren um. 
#    Seltene, spezifische Wörter (wie "Fussball") erhalten dabei mehr Gewicht als Füllwörter.
# 3. Kosinus-Ähnlichkeit (Cosine Similarity): Wir berechnen den Winkel zwischen dem 
#    Interessen-Vektor der Gruppe und dem Vektor des Events. 
#    Ein Wert von 1.0 bedeutet perfekte Übereinstimmung, 0.0 bedeutet keine.
# ----------------------------------------------------

def load_local_events(file_path="events.xlsx"):
    """
    Lädt Events aus einer Datei (Excel oder CSV).
    Unterstützt das Format: event_name, weekday (0=Mo...6=So), start_time, end_time, location, category
    Generiert daraus konkrete Termine für die nächsten 30 Tage.
    """
    generated_events = []
    
    try:
        # Automatische Erkennung ob Excel oder CSV
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        
        # Spaltennamen normalisieren (alles kleinschreiben)
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Prüfen, ob wir das "Weekly"-Format vor uns haben (Wochentage statt Datum)
        if 'weekday' in df.columns and 'event_name' in df.columns:
            today = datetime.now().date()
            
            # Wir generieren Events für die nächsten 30 Tage
            for i in range(30):
                current_date = today + timedelta(days=i)
                current_weekday = current_date.weekday() # 0 = Montag, 6 = Sonntag
                
                # Finde alle Events, die an diesem Wochentag stattfinden
                days_events = df[df['weekday'] == current_weekday]
                
                for _, row in days_events.iterrows():
                    try:
                        # Zeiten parsen
                        s_val = row['start_time']
                        e_val = row['end_time']

                        # Wenn es schon ein time-Objekt ist (Excel) oder String (CSV)
                        if isinstance(s_val, time): s_time = s_val
                        else: s_time = pd.to_datetime(str(s_val)).time()

                        if isinstance(e_val, time): e_time = e_val
                        else: e_time = pd.to_datetime(str(e_val)).time()
                        
                        # Volle Datetimes erstellen
                        start_dt = datetime.combine(current_date, s_time)
                        
                        # Check für Mitternachtsübergang
                        if e_time < s_time:
                            end_dt = datetime.combine(current_date + timedelta(days=1), e_time)
                        else:
                            end_dt = datetime.combine(current_date, e_time)

                        # Kategorie auslesen
                        cat = "Allgemein"
                        if 'category' in row: cat = row['category']
                        elif 'kategorie' in row: cat = row['kategorie']

                        # Event zur Liste hinzufügen
                        generated_events.append({
                            'Title': row['event_name'],
                            'Start': start_dt,
                            'End': end_dt,
                            'Category': cat, 
                            'Description': f"Ort: {row.get('location', 'Unbekannt')}"
                        })
                    except Exception as e:
                        continue
                        
            return pd.DataFrame(generated_events)

        # Fallback: Alte Struktur mit festen Daten
        else:
            if 'Start' in df.columns:
                df['Start'] = pd.to_datetime(df['Start']).dt.tz_localize(None)
            if 'End' in df.columns:
                df['End'] = pd.to_datetime(df['End']).dt.tz_localize(None)
            return df

    except FileNotFoundError:
        print(f"Datei '{file_path}' nicht gefunden.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return pd.DataFrame()

def check_user_availability(event_start, event_end, user_busy_slots):
    """Prüft Verfügbarkeit eines einzelnen Users."""
    for busy in user_busy_slots:
        b_start = busy['start'].replace(tzinfo=None)
        b_end = busy['end'].replace(tzinfo=None)
        
        # Konflikt bei Überlappung
        if (event_start < b_end) and (event_end > b_start):
            return False 
    return True

def find_best_slots_for_group(events_df, user_busy_map, selected_users, all_user_prefs, min_attendees=2):
    """
    Führt die Analyse durch:
    1. Filtert nach Zeit (Verfügbarkeit)
    2. Berechnet den ML-Score (Interessen-Matching)
    """
    if events_df.empty:
        return pd.DataFrame()

    results = []

    # --- SCHRITT 1: Verfügbarkeits-Analyse ---
    for _, event in events_df.iterrows():
        attendees = []
        
        for user in selected_users:
            busy_slots = user_busy_map.get(user, [])
            if check_user_availability(event['Start'], event['End'], busy_slots):
                attendees.append(user)
        
        # Nur Events behalten, wo genug Leute können
        if len(attendees) >= min_attendees:
            # Präferenzen NUR der Anwesenden sammeln
            attendee_prefs_text = ""
            for attendee in attendees:
                p_text = all_user_prefs.get(attendee, "")
                attendee_prefs_text += " " + p_text
            
            event_entry = event.copy()
            event_entry['attendees'] = ", ".join(attendees)
            event_entry['attendee_count'] = len(attendees)
            event_entry['group_prefs_text'] = attendee_prefs_text
            results.append(event_entry)

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)

    # --- SCHRITT 2: Machine Learning (TF-IDF & Cosine Similarity) ---
    
    # A) Feature Engineering: Wir bauen einen "Text-Blob" für jedes Event
    # Wir gewichten die Kategorie doppelt, da sie sehr wichtig ist
    result_df['event_features'] = (
        result_df['Title'].fillna('') + " " + 
        result_df['Category'].fillna('') + " " +  
        result_df['Category'].fillna('') + " " +  # Boost für Kategorie
        result_df['Description'].fillna('')
    )
    
    try:
        # B) Vektorisierung trainieren (Lernen des Vokabulars der Events)
        tfidf = TfidfVectorizer(stop_words='english')
        
        if len(result_df) < 2:
             result_df['match_score'] = 1.0 
        else:
            # Erstellt eine Matrix: Zeilen = Events, Spalten = Wörter
            tfidf_matrix = tfidf.fit_transform(result_df['event_features'])
            
            scores = []
            for idx, row in result_df.iterrows():
                # C) User-Präferenzen in den gleichen Vektorraum transformieren
                user_vector = tfidf.transform([row['group_prefs_text']])
                
                # D) Ähnlichkeit berechnen (Winkel zwischen Vektoren)
                sim = cosine_similarity(user_vector, tfidf_matrix[idx])
                scores.append(sim[0][0]) # Wert zwischen 0 und 1
                
            result_df['match_score'] = scores
    except Exception as e:
        print(f"ML Fehler: {e}")
        result_df['match_score'] = 0.5

    # Sortieren: Erst nach Anzahl Teilnehmer, dann nach ML-Score
    result_df = result_df.sort_values(by=['attendee_count', 'match_score'], ascending=[False, False])
    
    return result_df
