from datetime import datetime

def fetch_and_map_events(service, all_user_names):
    """
    Holt Events ab JETZT (Zukunft) und ordnet sie zu.
    Sammelt Diagnosedaten für die App.
    """
    # 1. Zeitraum: Ab jetzt (Standard)
    now = datetime.utcnow().isoformat() + 'Z'
    
    # Events holen
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=now, 
        maxResults=100, 
        singleEvents=True, 
        orderBy='startTime'
    ).execute()
    
    raw_events = events_result.get('items', [])
    
    user_busy_map = {name: [] for name in all_user_names}
    
    # Liste für die Diagnose (Das fehlte vorher!)
    debug_unassigned = [] 
    
    for event in raw_events:
        summary = event.get('summary', 'Ohne Titel').strip()
        
        # Nur nach 'dateTime' suchen (kein 'date' für Ganztagesevents)
        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')
        
        if start and end:
            s_dt = datetime.fromisoformat(start)
            e_dt = datetime.fromisoformat(end)
            
            assigned = False
            
            # Prüfen ob ein User-Name im Titel steckt
            for name in all_user_names:
                if name.lower() in summary.lower():
                    user_busy_map[name].append({
                        'summary': summary, 
                        'start': s_dt, 
                        'end': e_dt
                    })
                    assigned = True
            
            if not assigned:
                debug_unassigned.append(summary)
                
    # Hier bauen wir das Dictionary, das die app.py erwartet
    stats = {
        "total_events": len(raw_events),
        # Berechnen, wie viele zugeordnet wurden
        "assigned": len(raw_events) - len(debug_unassigned),
        # Das ist der Schlüssel, der den KeyError verursacht hat:
        "unassigned_titles": debug_unassigned 
    }
    
    return user_busy_map, stats
