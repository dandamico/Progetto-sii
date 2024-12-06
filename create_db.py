import sqlite3

# Connessione al database (crea il file se non esiste)
conn = sqlite3.connect('plugins/resturant/ristorante.db')

# Creazione di un cursore per eseguire comandi SQL
cursor = conn.cursor()

# Creazione della tabella "menu"
cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        prezzo REAL NOT NULL,
        quantità_ordinate_totale INTEGER DEFAULT 0
    )
''')

# Salvataggio delle modifiche
conn.commit()

menu_items = [
    ('Lasagna al Forno', 9.50, 0),
    ('Pizza Quattro Stagioni', 11.00, 0),
    ('Spaghetti allo Scoglio', 13.50, 0),
    ('Gelato alla Vaniglia', 4.00, 0)
]

# Inserimento dei dati nella tabella
cursor.executemany('''
    INSERT INTO menu (nome, prezzo, quantità_ordinate_totale)
    VALUES (?, ?, ?)
''', menu_items)

conn.commit()

# Creazione della tabella "ordini"
cursor.execute('''
    CREATE TABLE IF NOT EXISTS ordini (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT NOT NULL,
        id_menu INTEGER NOT NULL,
        FOREIGN KEY (id_menu) REFERENCES menu(id)
    )
''')

# Salvataggio delle modifiche
conn.commit()


# Creazione di due istanze di ordini
ordini_items = [
    ('John Doe', 1),  # Assumendo che l'id 1 corrisponda a 'Lasagna al Forno'
    ('Jane Doe', 2)   # Assumendo che l'id 2 corrisponda a 'Pizza Quattro Stagioni'
]

# Inserimento dei dati nella tabella ordini
cursor.executemany('''
    INSERT INTO ordini (cliente, id_menu)
    VALUES (?, ?)
''', ordini_items)

# Salvataggio delle modifiche
conn.commit()
# Chiusura della connessione
conn.close()