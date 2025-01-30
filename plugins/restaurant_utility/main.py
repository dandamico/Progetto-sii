import sqlite3
from cat.mad_hatter.decorators import tool
from cat.experimental.form import form, CatForm

@tool(
    return_direct=True,
    examples=["What does the menu offer?", "What's on the menu?", "What pizzas are on the menu?"]
)
def ask_menu(tool_input, cat):
    """
    Use this tool every time the customer wants to know what the menu offers, Input is always None
    """
    cat.send_ws_message("Sto cercando il menu")
    lista_pizze = get_all_items_in_menu()
    prompt = (
        f"Consider this list of pizzas:\n{lista_pizze}\n"
        "Present the list of pizzas to the customer as if you were introducing a menu\n"
        "You should say something like, 'This is what our menu offers... choose the pizza you like the most'"
    )
    return f"{prompt}"

@tool(
    return_direct=False,
    examples=["How much ... cost?"]
)
def get_pizza_price(tool_input: str, cat):
    """
    input is always an element present on menu,
    input is always the menu item the user wants to know the price of,
    input is always present in user's question,
    how much margherita cost? in this example the input is "margherita"
    """
    cat.send_ws_message("Sto cercando il prezzo")
    print(tool_input)

    result = [get_price_of_item_in_menu(tool_input)]
    print("RESULT IS: " + str(result))
    if result:
        print("ENTRATO NELL'IF E RESULT[0] IS: " + str(result[0]))
        res = str(result[0])
        prompt = (
            f"Consider this price food:\n{res}\n"
            "Present the price food to the customer\n"
            f"You should say something like, 'the price you asked me is:{res}\n'"
        )
        return f"{prompt}"
    else:
        prompt = (
            "the item wanted by the customer is not on the menu\n"
            f"You should say something like, 'the item you asked for is not on the menu\n'"
        )
        return f"{prompt}"

def get_all_items_in_menu():
    conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
    cursor = conn.cursor()
    query = "SELECT nome FROM menu;"
    # Esecuzione della query con il parametro
    cursor.execute(query)
    risultato = cursor.fetchall()
    # Chiusura della connessione
    conn.close()
    #lista_pizze = [item[0] for item in risultato]
    lista_pizze = [item[0].replace("_", " ") for item in risultato]
    return lista_pizze


def get_price_of_item_in_menu(tool_input):
    conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
    cursor = conn.cursor()
    tool_input = tool_input.lower().replace(" ", "_")
    query = "SELECT prezzo FROM menu WHERE nome = ? LIMIT 1;"
    cursor.execute(query, (tool_input,))
    result = cursor.fetchone()
    conn.close()
    prezzo = result[0]
    return prezzo if result else None


def add_order_and_remove_rimanenze(nome_piatto):
    try:
        conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
        print((nome_piatto,))
        piatto = nome_piatto.lower()
        cursor = conn.cursor()
        cursor.execute('''
                UPDATE menu
                SET quantità_ordinate_totali = quantità_ordinate_totali + 1,
                    rimanenze_magazzino = rimanenze_magazzino - 1
                WHERE nome = ?
            ''', (piatto,))  # Il parametro deve essere passato come tupla
        conn.commit()
        conn.close()
        return "Database aggiornato per l'item: " + str(piatto)
    except sqlite3.OperationalError as e:
        return e


