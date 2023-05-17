import sqlite3

con = sqlite3.connect("reactionSound.db")
cur = con.cursor()

def create_table():
    cur.execute("CREATE TABLE IF NOT EXISTS reactionSound(id INTEGER PRIMARY KEY, reaction TEXT NOT NULL UNIQUE, sound TEXT NOT NULL)")

def data_entry(reaction, sound):
    cur.execute("INSERT OR IGNORE INTO reactionSound(reaction, sound) VALUES (?, ?)", (reaction, sound))
    con.commit()

def view_all():
    cur.execute("SELECT * FROM reactionSound")
    data = cur.fetchall()
    return data

def view_one(reaction):
    cur.execute("SELECT * FROM reactionSound WHERE reaction = ?", (reaction,))
    data = cur.fetchall()
    return data




if __name__ == "__main__":
    
    create_table()
    #data_entry(":drum_with_drumsticks:", "jungle.mp3")
    
    #print number of rows in table
    print(len(view_all()))
    print(view_all())
    
    #print(view_one(":zombie:"))
    