import sqlite3

DB_PATH = "user_database.sqlite"

def init_db():
    """Initialisiert die Datenbank und erstellt Tabellen."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. User Tabelle
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            preferences TEXT
        )
    """)
    
    # 2. NEU: Gespeicherte Events Tabelle
    c.execute("""
        CREATE TABLE IF NOT EXISTS saved_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            start_time TEXT,
            end_time TEXT,
            color TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(name, email, preferences):
    """Fügt einen User hinzu."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    prefs_str = ",".join(preferences) if isinstance(preferences, list) else preferences
    
    try:
        if email and email.strip() != "":
            c.execute("SELECT id FROM users WHERE email = ?", (email,))
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                    UPDATE users 
                    SET name = ?, preferences = ? 
                    WHERE email = ?
                """, (name, prefs_str, email))
                operation = "updated"
            else:
                c.execute("""
                    INSERT INTO users (name, email, preferences)
                    VALUES (?, ?, ?)
                """, (name, email, prefs_str))
                operation = "created"
        else:
            import uuid
            dummy_email = f"no_email_{uuid.uuid4()}@local"
            c.execute("""
                INSERT INTO users (name, email, preferences)
                VALUES (?, ?, ?)
            """, (name, dummy_email, prefs_str))
            operation = "created_no_email"

        conn.commit()
        return True, operation
    except Exception as e:
        print(f"Database Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, preferences FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

# --- NEUE FUNKTIONEN FÜR EVENTS ---

def add_saved_event(title, start, end, color):
    """Speichert ein ausgewähltes Event in der DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Prüfen ob es schon existiert (einfacher Check auf Titel & Zeit)
        c.execute("SELECT id FROM saved_events WHERE title = ? AND start_time = ?", (title, start))
        if c.fetchone():
            return False # Existiert schon
            
        c.execute("""
            INSERT INTO saved_events (title, start_time, end_time, color)
            VALUES (?, ?, ?, ?)
        """, (title, start, end, color))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def get_saved_events():
    """Holt alle gespeicherten Events."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Damit wir Spaltennamen nutzen können
    c = conn.cursor()
    c.execute("SELECT title, start_time as start, end_time as end, color as backgroundColor, color as borderColor FROM saved_events")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def clear_saved_events():
    """Löscht alle gespeicherten Events."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM saved_events")
    conn.commit()
    conn.close()
