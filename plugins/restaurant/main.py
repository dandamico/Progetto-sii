import json
from fileinput import hook_encoded
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from cat.mad_hatter.decorators import tool
from cat.mad_hatter.decorators import hook
from cat.experimental.form import form, CatForm, CatFormState
from ..restaurant_utility.main import get_all_items_in_menu, get_price_of_item_in_menu

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

# @hook
# def before_cat_sends_message(message, cat):
#     active_form = cat.working_memory.active_form
#     cat.send_ws_message("PORCO DE DIO MALEDETTO CANE SCHIFOSO LURIDO VERONA HA PERSO")
#     message["content"] = str(message["content"]) + str(active_form.form_data)
#     return message


# Define the base model for a pizza order
class PizzaOrder(BaseModel):
    items: List[str] = Field(..., description="List of item in menu requested by the customer (e.g., margherita, boscaiola)")
    #delivery: bool = Field(..., description="True if the customer wants delivery, False for pickup")
    customer_name: str = Field(None, description="Customer's name")
    #desired_time: str = Field(..., description="Desired time for delivery or pickup (format: HH:MM)")
    notes: Optional[str] = Field(None, description="Additional notes (e.g., no onions, extra spicy oil)")
    total: Optional[float] = Field(None, description="Total price of items in order requested by the customer")
    #confirmed: bool = Field(False, description="Confirmed status of order", )

    # Validator to ensure the items list is not empty
    @field_validator("items")
    @classmethod
    def check_elem_exist(cls, v, info: ValidationInfo) -> str:
        if not isinstance(v, list):
            raise ValueError("Items must be a list of strings.")

        list_menu_item = get_all_items_in_menu()
        print("LISTA MENU: ")
        print(list_menu_item)
        for item in v:
            print("ITEM: " + item)
            if item not in list_menu_item:
                raise ValueError(f"Item '{item}' is not present in the menu list.")
        return v

    @field_validator("customer_name")
    @classmethod
    def customer_validator(cls, v):
        # if not isinstance(v, str):
        #     raise ValueError("Customer name must be a string.")
        if v is None:
            raise ValueError("Customer name cannot be None.")
        return v

    # Validator to check if the desired time is available
    # @field_validator("desired_time")
    # @classmethod
    # def check_availability(cls, v: str, info: ValidationInfo) -> str:
    #     if v in fake_db:
    #         raise ValueError("The desired time is already taken")
    #     return v


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
    model_class.items = []

    # Method to handle form submission
    def submit(self, form_data):
        # Simulate saving the order via an API request
        # requests.post("https://{your_fancy_pizza_api}/api/orders", json=form_data)
        # Generate a response summarizing the completed order

        # Generate a response summarizing the completed order
        self.cat.send_ws_message("SUBMIT FUNCTION")
        print("FORM DATA: ", form_data)
        # lista_ordinato = form_data.get('items', [])
        # totale = 0
        # for elem in lista_ordinato:
        #     totale += get_price_of_item_in_menu(elem)
        # tot = str(totale)
        prompt = (
            f"The pizza order is complete. The details are: {form_data}. "
            "Respond with something like: 'Alright, your pizza is officially on its way.'"
        )
        return {"output": self.cat.llm(prompt)}

    # Handle the situation where the user cancels the form
    def message_closed(self):
        self.cat.send_ws_message("MESSAGE CLOSED FUNCTION")
        prompt = (
            "The customer is not hungry anymore. Respond with a short and bothered answer."
        )
        return {"output": self.cat.llm(prompt)}

    # Generate a sarcastic confirmation message
    def message_wait_confirm(self):
        self.cat.send_ws_message("MESSAGE WAIT_CONFIRM FUNCTION")
        prompt = (
            "Summarize the collected details kindly and professionally and after ask the customer if he want to confirm the information and proceed with the order or not \n"
            f"{self._generate_base_message()}\n"
           # "Say something like, 'So, this is what we’ve got ... Do you want to confirm?'"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    # Handle incomplete form inputs with a nudge
    def message_incomplete(self):
        self.cat.send_ws_message("MESSAGE INCOMPLETE  FUNCTION")
        prompt = (
            f"The form is missing some details:\n{self._generate_base_message()}\n"
            "Based on the missing information, kindly and professionally ask the customer to provide the necessary details"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    def update(self):
        # Conversation to JSON
        self.cat.send_ws_message("UPDATE FUNCTION")

        #EXTRACT
        json_details = self.extract()   #{'items': ['margherita'], 'customer_name': None, 'notes': None, 'total': 0}

        #UPDATE TOTAL
        lista_ordinato = json_details.get('items', [])
        tot = 0
        for elem in lista_ordinato:
            tot += get_price_of_item_in_menu(elem)
        json_details['total'] = tot

        #json_details['confirmed'] = False

        json_details = self.sanitize(json_details)     #{'items': ['margherita']}
        print("JSON DETAILS AFTER SANITIZE:")
        print(json_details)

        # model merge old and new
        new_model = self._model | json_details         #{'items': ['margherita']}
        print("NEW MODEL: ")
        print(new_model)

        # Validate new_details
        new_model = self.validate(new_model)           #{'items': ['margherita'], 'customer_name': None, 'notes': None}
        print("NEW MODEL AFTER VALIDATE: ")
        print(new_model)

        return new_model

    # Check user confirm the form data
    def confirm(self) -> bool:
        # Get user message
        user_message = self.cat.working_memory.user_message_json.text

        # Confirm prompt
        confirm_prompt = f"""Your task is to produce a JSON representing whether a user is confirming or not.
                             If the user wants to order other things it means that he don't want to confirm.
                             Responses like 'no, I want to order something else' indicate that the user does not want to confirm.
                                JSON must be in this format:
                                ```json
                                {{
                                    "confirm": // type boolean, must be `true` or `false` 
                                }}
                                ```
                                
                                User said "{user_message}"
                                
                                JSON:
                                {{
                        "confirm": """

        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(confirm_prompt)
        return "true" in response.lower()

    # # Execute the dialogue step
    # def next(self):
    #     # could we enrich prompt completion with episodic/declarative memories?
    #     # self.cat.working_memory.episodic_memories = []
    #
    #     # If state is WAIT_CONFIRM, check user confirm response..
    #     if self._state == CatFormState.WAIT_CONFIRM:
    #         if self.confirm():
    #             self._state = CatFormState.CLOSED
    #             return self.submit(self._model)
    #         else:
    #             if self.check_exit_intent():
    #                 self._state = CatFormState.CLOSED
    #             else:
    #                 self._state = CatFormState.INCOMPLETE
    #
    #
    #     if self.check_exit_intent():
    #         self._state = CatFormState.CLOSED
    #
    #     # If the state is INCOMPLETE, execute model update
    #     # (and change state based on validation result)
    #     if self._state == CatFormState.INCOMPLETE:
    #         self._model = self.update()
    #
    #
    #
    #     # If state is COMPLETE, ask confirm (or execute action directly)
    #     if self._state == CatFormState.COMPLETE:
    #         if self.check_exit_intent():
    #             self._state = CatFormState.CLOSED
    #         if self.ask_confirm:
    #             self._state = CatFormState.WAIT_CONFIRM
    #         else:
    #             self._state = CatFormState.CLOSED
    #             return self.submit(self._model)
    #
    #     # if state is still INCOMPLETE, recap and ask for new info
    #     return self.message()