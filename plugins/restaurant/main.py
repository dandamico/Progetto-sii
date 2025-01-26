# import sqlite3
# from timeit import repeat
# from typing import Optional, List
# from pydantic import BaseModel, Field, field_validator, ValidationInfo
# #import sqlite3
# from cat.experimental.form import form, CatForm
#
# # from .cat_form import CatForm
#
# # A fake database to simulate existing orders at certain times
# fake_db = {
#     "21:00": {
#         "pizzas": ["Margherita", "Pepperoni"],
#         "delivery": False,
#         "customer_name": "John Doe",
#         "desired_time": "21:00",
#         "notes": "No onions, extra spicy oil",
#     },
#     "22:00": {
#         "pizzas": ["Margherita", "Pepperoni"],
#         "delivery": True,
#         "customer_name": "Jane Didoe",
#         "desired_time": "22:00",
#         "notes": "No onions, extra spicy oil",
#         "address": "123 Main St, Anytown, USA",
#     },
# }
#
# conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
# cursor = conn.cursor()
# query = "SELECT * FROM menu;"
# # Esecuzione della query con il parametro
# cursor.execute(query)
# risultato = cursor.fetchall()
# # Chiusura della connessione
# conn.close()
# lista_pizze = risultato
#
#
#
# # Define the base model for a pizza order
# class PizzaOrder(BaseModel):
#     pizzas: List[str] = Field(..., description="Elenco delle pizze che il cliente vorrebbe ordinare")
#     delivery: bool = Field(..., description="True se il cliente vuole farsi consegnare la pizza, False se il cliente la viene a prendere")
#     customer_name: str = Field(None, description="Nome del cliente che effetua l'ordine")
#     desired_time: str = Field(..., description="Orario della consegna (format: HH:MM)")
#     notes: Optional[str] = Field(None, description="Note addizionali (e.g., no cipolle, olio piccante extra")
#
#     # Validator to ensure the pizzas list is not empty
#     @field_validator("pizzas")
#     @classmethod
#     def check_empty_list(cls, v: str, info: ValidationInfo) -> str:
#         if not v:
#             raise ValueError("List cannot be empty")
#         return v
#
#
#     @field_validator("pizzas")
#     @classmethod
#     def check_pizza_exist(cls, input_pizza: str, info: ValidationInfo):
#         conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
#         cursor = conn.cursor()
#         print(input_pizza)
#         query = "SELECT * FROM menu WHERE nome = ? LIMIT 1;"
#
#         print(query)
#         # Esecuzione della query con il parametro
#         cursor.execute(query, (str(input_pizza),))
#         risultato = cursor.fetchone()
#         # Chiusura della connessione
#         conn.close()
#         pizza_form = PizzaForm()
#         if risultato is not None:
#             pizza_form.message_wait_confirm()
#         else:
#             pizza_form.repeat(input_pizza)
#
#     # Validator to check if the desired time is available
#     @field_validator("desired_time")
#     @classmethod
#     def check_availability(cls, v: str, info: ValidationInfo) -> str:
#         if v in fake_db:
#             raise ValueError("The desired time is already taken")
#         return v
#
#
# # A specialized model for pizza orders that include delivery
# class PizzaOrderWithDelivery(PizzaOrder):
#     address: str = Field(..., description="Delivery address")
#
#
# # forms let you control goal oriented conversations
# @form
# class PizzaForm(CatForm):
#     description = "Pizza Order"
#     model_class = PizzaOrder
#     start_examples = [
#         "vorrei ordinare della pizza",
#         "vorrei ordinare la cena",
#         "vorrei ordinare il pranzo",
#         "voglio mangiare"
#     ]
#     stop_examples = [
#         "a posto cosi",
#         "apposto cosi",
#         "non voglio altro",
#         "va bene cosi",
#         "non voglio altro",
#         "voglio terminare il mio ordine "
#     ]
#     # Ask for confirmation before finalizing
#     ask_confirm = True
#
#     # Dynamically select the model based on user input
#     def model_getter(self):
#         # If delivery is requested, use the PizzaOrderWithDelivery model
#         if "delivery" in self._model and self._model["delivery"]:
#             self.model_class = PizzaOrderWithDelivery
#         else:
#             # Otherwise, use the base PizzaOrder model
#             self.model_class = PizzaOrder
#         return self.model_class
#
#     # Method to handle form submission
#     def submit(self, form_data):
#
#         # Simulate saving the order via an API request
#         # requests.post("https://{your_fancy_pizza_api}/api/orders", json=form_data)
#         # Generate a response summarizing the completed order
#
#         # Generate a response summarizing the completed order
#         prompt = (
#             f"L'ordine è completo, ti ripeto quello che hai ordinato per sicurezza: {form_data}. "
#             "Rispondi qualcosa del tipo: 'perfetto! stiamo preparando la tua pizza!.'"
#         )
#         return {"output": self.cat.llm(prompt)}
#
#     def repeat(self, input_req):
#         prompt = (
#             "L'oggetto richiesto " + input_req + "non è presente sul menu riscrivimi cosa desideri"
#         )
#         return {"output": self.cat.llm(prompt)}
#
#     # Handle the situation where the user cancels the form
#     def message_closed(self):
#         prompt = (
#             "il cliente è soddisfatto e vuole terminare l'ordine. rispondi qualcosa del tipo :'va bene spero che sia tutto di suo gradimento e ci vediamo alla prossima'."
#         )
#         return {"output": self.cat.llm(prompt)}
#
#     # Generate a sarcastic confirmation message
#     def message_wait_confirm(self):
#         prompt = (
#             "ripeti al cliente quello che ha ordinato :\n"
#             f"{self._generate_base_message()}\n"
#             "di qualcosa del tipo: 'ecco a te le pietanze che hai ordinato, desideri connfermare l'ordine?'"
#         )
#         return {"output": f"{self.cat.llm(prompt)}"}
#
#     # Handle incomplete form inputs with a nudge
#     def message_incomplete(self):
#         prompt = (
#             f"Per completare l' ordine mancano alcuni dettagli:\n{self._generate_base_message()}\n"
#             "basandoti su quello che manca rispondi qualcosa per sollecitare il cliente a fornire le informazioni mancanti ."
#         )
#         return {"output": f"{self.cat.llm(prompt)}"}
import sqlite3
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from cat.mad_hatter.decorators import tool
from cat.experimental.form import form, CatForm

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
        "customer_name": "Jane Doe",
        "desired_time": "22:00",
        "notes": "No onions, extra spicy oil",
        "address": "123 Main St, Anytown, USA",
    },
}


# @tool(
#     return_direct=True,
#     examples=["What does the menu offer?", "What's on the menu?", "What pizzas are on the menu?"]
# )
# def ask_menu(tool_input, cat):
#     """
#     Use this tool every time the customer wants to know what the menu offers, Input is always None
#     """
#     cat.send_ws_message("Sto cercando il menu")
#     conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
#     cursor = conn.cursor()
#     query = "SELECT nome FROM menu;"
#     # Esecuzione della query con il parametro
#     cursor.execute(query)
#     risultato = cursor.fetchall()
#     # Chiusura della connessione
#     conn.close()
#     lista_pizze = risultato
#     prompt = (
#         f"Consider this list of pizzas:\n{lista_pizze}\n"
#         "Present the list of pizzas to the customer as if you were introducing a menu\n"
#         "You should say something like, 'This is what our menu offers... choose the pizza you like the most'"
#     )
#     return f"{prompt}"
#
# @tool(
#     return_direct=True,
#     examples=["How much ... cost?"]
# )
# def get_pizza_price(tool_input: str, cat):
#     """
#     input is always an element present on menu,
#     input is always the menu item the user wants to know the price of,
#     input is always present in user's question,
#     how much margherita cost? in this example the input is "margherita"
#     """
#     cat.send_ws_message("Sto cercando il prezzo")
#     conn = sqlite3.connect('/app/cat/plugins/restaurant/ristorante.db')
#     cursor = conn.cursor()
#     query = "SELECT prezzo FROM menu WHERE nome = ? LIMIT 1;"
#     cursor.execute(query, (tool_input,))
#     result = cursor.fetchone()
#     conn.close()
#     print("RESULT IS: " + str(result))
#     if result:
#         print("ENTRATO NELL'IF E RESULT[0] IS: " + str(result[0]))
#         res = str(result[0])
#         prompt = (
#             f"Consider this price food:\n{res}\n"
#             "Present the price food to the customer\n"
#             f"You should say something like, 'the price you asked me is:{res}\n'"
#         )
#         return f"{prompt}"
#     else:
#         prompt = (
#             "the item wanted by the customer is not on the menu\n"
#             f"You should say something like, 'the item you asked for is not on the menu\n'"
#         )
#         return f"{prompt}"




# Define the base model for a pizza order
class PizzaOrder(BaseModel):
    pizzas: List[str] = Field(..., description="List of pizzas requested by the customer (e.g., Margherita, Pepperoni)")
    delivery: bool = Field(..., description="True if the customer wants delivery, False for pickup")
    customer_name: str = Field(None, description="Customer's name")
    desired_time: str = Field(..., description="Desired time for delivery or pickup (format: HH:MM)")
    notes: Optional[str] = Field(None, description="Additional notes (e.g., no onions, extra spicy oil)")

    # Validator to ensure the pizzas list is not empty
    @field_validator("pizzas")
    @classmethod
    def check_empty_list(cls, v: str, info: ValidationInfo) -> str:
        if not v:
            raise ValueError("List cannot be empty")
        return v

    # Validator to check if the desired time is available
    @field_validator("desired_time")
    @classmethod
    def check_availability(cls, v: str, info: ValidationInfo) -> str:
        if v in fake_db:
            raise ValueError("The desired time is already taken")
        return v


# A specialized model for pizza orders that include delivery
# class PizzaOrderWithDelivery(PizzaOrder):
#     address: str = Field(..., description="Delivery address")


# forms let you control goal oriented conversations
@form
class PizzaForm(CatForm):
    description = "A form that is triggered when the user wants to start an order at the restaurant."
    model_class = PizzaOrder
    start_examples = [
        "I want to place an order",
        "I want a pizza",
        "Hi, I would like to order a pizza",
        "Hi, I would like to order"
    ]
    stop_examples = [
        "stop pizza order",
        "not hungry anymore",
    ]
    # Ask for confirmation before finalizing
    ask_confirm = True

    # # Dynamically select the model based on user input
    # def model_getter(self):
    #     # If delivery is requested, use the PizzaOrderWithDelivery model
    #     if "delivery" in self._model and self._model["delivery"]:
    #         self.model_class = PizzaOrderWithDelivery
    #     else:
    #         # Otherwise, use the base PizzaOrder model
    #         self.model_class = PizzaOrder
    #     return self.model_class


    # Method to handle form submission
    def submit(self, form_data):

        # Simulate saving the order via an API request
        # requests.post("https://{your_fancy_pizza_api}/api/orders", json=form_data)
        # Generate a response summarizing the completed order

        # Generate a response summarizing the completed order
        prompt = (
            f"The pizza order is complete. The details are: {form_data}. "
            "Respond with something like: 'Alright, your pizza is officially on its way.'"
        )
        return {"output": self.cat.llm(prompt)}

    # Handle the situation where the user cancels the form
    def message_closed(self):
        prompt = (
            "The customer is not hungry anymore. Respond with a short and bothered answer."
        )
        return {"output": self.cat.llm(prompt)}

    # Generate a sarcastic confirmation message
    def message_wait_confirm(self):
        prompt = (
            "Summarize the collected details briefly and sarcastically:\n"
            f"{self._generate_base_message()}\n"
            "Say something like, 'So, this is what we’ve got ... Do you want to confirm?'"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    # Handle incomplete form inputs with a nudge
    def message_incomplete(self):
        prompt = (
            f"The form is missing some details:\n{self._generate_base_message()}\n"
            "Based on what’s still needed, craft a sarcastic yet professional nudge. Very short since it is a busy restaurant."
            "For example, if 'address' is missing, say: 'I’m good, but I’m not a mind reader. Where should I deliver this masterpiece?' "
        )
        return {"output": f"{self.cat.llm(prompt)}"}