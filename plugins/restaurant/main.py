# import sqlite3
# from cat.mad_hatter.decorators import tool, hook
# from pydantic import Field, field_validator
# from cat.log import log
#
# @tool
# def order(input, cat):
#     """Voglio della pizza
#     vorrei ordinare della pizza
#     prendo delle pizze
#     prendo una pizza
#     I'll take a Margherita pizza
#     L'input è la parola che viene dopo la frase- voglio ordinare una pizza"""
#     log.critical("INZIATO ORDINE PIZZA")
#
#     conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
#     cursor = conn.cursor()
#     print(input)
#     query = "SELECT * FROM menu WHERE nome = ?;"
#
#     print(query)
#     # Esecuzione della query con il parametro
#     cursor.execute(query, (str(input),))
#     risultato = cursor.fetchone()
#     # Chiusura della connessione
#     conn.close()
#     print(risultato)
#     return print("ciao")
import sqlite3
from timeit import repeat
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo
#import sqlite3
from cat.experimental.form import form

from plugins.restaurant.cat_form import CatForm

# A fake database to simulate existing orders at certain times
fake_db = {
    "21:00": {
        "pizzas": ["Margherita", "Pepperoni"],
        "delivery": False,
        "customer_name": "John Doe",
        "desired_time": "21:00",
        "notes": "No onions, extra spicy oil",
    },
    "22:00": {
        "pizzas": ["Margherita", "Pepperoni"],
        "delivery": True,
        "customer_name": "Jane Didoe",
        "desired_time": "22:00",
        "notes": "No onions, extra spicy oil",
        "address": "123 Main St, Anytown, USA",
    },
}

conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
cursor = conn.cursor()
query = "SELECT * FROM menu;"
# Esecuzione della query con il parametro
cursor.execute(query)
risultato = cursor.fetchall()
# Chiusura della connessione
conn.close()
lista_pizze = risultato



# Define the base model for a pizza order
class PizzaOrder(BaseModel):
    pizzas: List[str] = Field(..., description="Elenco delle pizze che il cliente vorrebbe ordinare")
    delivery: bool = Field(..., description="True se il cliente vuole farsi consegnare la pizza, False se il cliente la viene a prendere")
    customer_name: str = Field(None, description="Nome del cliente che effetua l'ordine")
    desired_time: str = Field(..., description="Orario della consegna (format: HH:MM)")
    notes: Optional[str] = Field(None, description="Note addizionali (e.g., no cipolle, olio piccante extra")

    # Validator to ensure the pizzas list is not empty
    @field_validator("pizzas")
    @classmethod
    def check_empty_list(cls, v: str, info: ValidationInfo) -> str:
        if not v:
            raise ValueError("List cannot be empty")
        return v


    @field_validator("pizzas")
    @classmethod
    def check_pizza_exist(cls, input_pizza: str, info: ValidationInfo):
        conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
        cursor = conn.cursor()
        print(input_pizza)
        query = "SELECT * FROM menu WHERE nome = ? LIMIT 1;"

        print(query)
        # Esecuzione della query con il parametro
        cursor.execute(query, (str(input_pizza),))
        risultato = cursor.fetchone()
        # Chiusura della connessione
        conn.close()
        pizza_form = PizzaForm()
        if risultato is not None:
            pizza_form.message_wait_confirm()
        else:
            pizza_form.repeat(input_pizza)

    # Validator to check if the desired time is available
    @field_validator("desired_time")
    @classmethod
    def check_availability(cls, v: str, info: ValidationInfo) -> str:
        if v in fake_db:
            raise ValueError("The desired time is already taken")
        return v


# A specialized model for pizza orders that include delivery
class PizzaOrderWithDelivery(PizzaOrder):
    address: str = Field(..., description="Delivery address")


# forms let you control goal oriented conversations
@form
class PizzaForm(CatForm):
    description = "Pizza Order"
    model_class = PizzaOrder
    start_examples = [
        "vorrei ordinare della pizza",
        "vorrei ordinare la cena",
        "vorrei ordinare il pranzo",
        "voglio mangiare"
    ]
    stop_examples = [
        "a posto cosi",
        "apposto cosi",
        "non voglio altro",
        "va bene cosi",
        "non voglio altro",
        "voglio terminare il mio ordine "
    ]
    # Ask for confirmation before finalizing
    ask_confirm = True

    # Dynamically select the model based on user input
    def model_getter(self):
        # If delivery is requested, use the PizzaOrderWithDelivery model
        if "delivery" in self._model and self._model["delivery"]:
            self.model_class = PizzaOrderWithDelivery
        else:
            # Otherwise, use the base PizzaOrder model
            self.model_class = PizzaOrder
        return self.model_class

    # Method to handle form submission
    def submit(self, form_data):

        # Simulate saving the order via an API request
        # requests.post("https://{your_fancy_pizza_api}/api/orders", json=form_data)
        # Generate a response summarizing the completed order

        # Generate a response summarizing the completed order
        prompt = (
            f"L'ordine è completo, ti ripeto quello che hai ordinato per sicurezza: {form_data}. "
            "Rispondi qualcosa del tipo: 'perfetto! stiamo preparando la tua pizza!.'"
        )
        return {"output": self.cat.llm(prompt)}

    def repeat(self, input_req):
        prompt = (
            "L'oggetto richiesto " + input_req + "non è presente sul menu riscrivimi cosa desideri"
        )
        return {"output": self.cat.llm(prompt)}

    # Handle the situation where the user cancels the form
    def message_closed(self):
        prompt = (
            "il cliente è soddisfatto e vuole terminare l'ordine. rispondi qualcosa del tipo :'va bene spero che sia tutto di suo gradimento e ci vediamo alla prossima'."
        )
        return {"output": self.cat.llm(prompt)}

    # Generate a sarcastic confirmation message
    def message_wait_confirm(self):
        prompt = (
            "ripeti al cliente quello che ha ordinato :\n"
            f"{self._generate_base_message()}\n"
            "di qualcosa del tipo: 'ecco a te le pietanze che hai ordinato, desideri connfermare l'ordine?'"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    # Handle incomplete form inputs with a nudge
    def message_incomplete(self):
        prompt = (
            f"Per completare l' ordine mancano alcuni dettagli:\n{self._generate_base_message()}\n"
            "basandoti su quello che manca rispondi qualcosa per sollecitare il cliente a fornire le informazioni mancanti ."
        )
        return {"output": f"{self.cat.llm(prompt)}"}