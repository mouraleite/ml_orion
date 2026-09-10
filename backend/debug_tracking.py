import sqlite3

def check():
    conn = sqlite3.connect('viabilidades.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, id_sienge, nome FROM cost_centers WHERE track_in_dashboard=1")
        ccs = cursor.fetchall()
        print("Tracked CCs:", len(ccs))
        
        from collections import defaultdict
        cc_groups = defaultdict(list)
        for row in ccs:
            cid, id_sienge, nome = row
            if id_sienge and len(id_sienge) >= 3:
                base_class = id_sienge[:3]
            else:
                base_class = str(cid)
            cc_groups[base_class].append(row)
        
        for base, cclist in cc_groups.items():
            print(f"Group {base}: {[c[2] for c in cclist]}")
            
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    check()
