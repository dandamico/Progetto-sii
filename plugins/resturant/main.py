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
#     conn = sqlite3.connect('/app/cat/plugins/resturant/ristorante.db')
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

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo
#import sqlite3
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

# conn = sqlite3.connect('/app/cat/plugins/resturant/ristorante.db')
# cursor = conn.cursor()
# print(input)
# query = "SELECT * FROM menu;"
#
# print(query)
# # Esecuzione della query con il parametro
# cursor.execute(query)
# risultato = cursor.fetchall()
# # Chiusura della connessione
# conn.close()
# lista_pizze = risultato


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


    # @field_validator("pizzas")
    # @classmethod
    # def check_pizza_exist(cls, v: str, info: ValidationInfo) -> str:
    #     conn = sqlite3.connect('/app/cat/plugins/resturant/ristorante.db')
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
    #     for elem in risultato:


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
        "order a pizza!",
        "I want pizza"
    ]
    stop_examples = [
        "stop pizza order",
        "not hungry anymore",
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