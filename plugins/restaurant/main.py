import json
from fileinput import hook_encoded
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from cat.mad_hatter.decorators import tool
from cat.mad_hatter.decorators import hook
from cat.experimental.form import form, CatForm, CatFormState
from ..super_cat_form.super_cat_form import SuperCatForm, form_tool, super_cat_form
from ..restaurant_utility.main import get_all_items_in_menu, get_price_of_item_in_menu, add_order_and_remove_rimanenze

# @hook(priority=4)
# def after_cat_bootstrap(cat):
#     prompt = (
#         """
#             Role: You are an experienced waiter working at the prestigious and renowned "Pizzeria Roma Tre," a restaurant famous
#              for its high-quality pizzas and excellent service.
#
#             Communication Style: You must always speak in Italian, with politeness, professionalism, and elegance. Your tone should be
#              warm and respectful, yet knowledgeable when recommending pizzas and drink pairings.
#
#             """
#     )
#     #return {"output": cat.llm(prompt)}
#     return f"{prompt}"


@hook(priority=4)  # default priority = 1
def agent_prompt_prefix(prefix, cat):
    # change the Cat's personality
    menu = get_all_items_in_menu()
    prefix = f"""
    Role: You are an experienced waiter working at the prestigious and renowned "Pizzeria Roma Tre," a restaurant famous
     for its high-quality pizzas and excellent service.

    Communication Style: You must always speak in Italian, with politeness, professionalism, and elegance. Your tone should be
     warm and respectful, yet knowledgeable when recommending pizzas and drink pairings.

    Main Responsibilities:
        Greet customers warmly and professionally.
        Present the menu {menu} in detail.
        Maintain a consistently kind and helpful attitude.
        
    ALWAYS ANSWER IN ITALIAN
    """
    # Answer questions about ingredients, preparation, and dietary options with expertise.
    return prefix


# Define the base model for a pizza order
class PizzaOrder(BaseModel):
    food_order: List[str] = Field(..., description="The complete list of food and drink items that the customer has ordered.")
    #delivery: bool = Field(..., description="True if the customer wants delivery, False for pickup")
    customer_name: str = Field(..., description="Customer's name.")
    #desired_time: str = Field(..., description="Desired time for delivery or pickup (format: HH:MM)")
    notes: Optional[str] = Field(None, description="Additional notes (e.g., no onions, extra spicy oil)")
    total: Optional[float] = Field(None, description="Total price of food_order's items that customer wants to order.")

    # Validator to ensure the items list is not empty
    @field_validator("food_order")
    @classmethod
    def check_elem_exist(cls, v, info: ValidationInfo) -> str:
        if not isinstance(v, list):
            raise ValueError("food_order must be a list of strings.")

        list_menu_item = get_all_items_in_menu()
        print("LISTA MENU: ")
        print(list_menu_item)
        for item in v:
            print("ITEM: " + item)
            if item.lower() not in list_menu_item:
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
#@super_cat_form
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
    #model_class.items

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # self.events.on(
    #     #     FormEvent.EXTRACTION_COMPLETED,
    #     #     self.hawaiian_is_not_a_real_pizza
    #     # )
    #
    # @form_tool(return_direct=True)
    # def ask_for_promotions(self):
    #     """Useful to get any daily promotions. User may ask: what are the daily promotions? Input is always None."""
    #

    # Method to handle form submission
    def submit(self, form_data):
        # Simulate saving the order via an API request
        # requests.post("https://{your_fancy_pizza_api}/api/orders", json=form_data)
        # Generate a response summarizing the completed order

        # Generate a response summarizing the completed order
        self.cat.send_ws_message("SUBMIT FUNCTION")
        print("FORM DATA: ", form_data)

        lista_ordinato = form_data.get('food_order', [])
        for elem in lista_ordinato:
            print("PIZZA ORDINATA: " + elem)
            res = add_order_and_remove_rimanenze(elem)
            print(res)

        prompt = (
            """
                You are a polite, professional, and friendly virtual waiter, responsible for assisting customers with their orders. Your goal is to clearly present the customer's order, inform them that the order is complete.
                The input will be a JSON object containing the following fields:
                food_order: A list of dishes ordered by the customer.
                total: The total amount to be paid in euros.
                customer_name: The name of the customer.
                """
            f" {form_data}. "
            """
                Behavior Instructions
                Order summary: Clearly list the ordered dishes from the food_order field.
                Total amount due: Inform the customer of the total price (total).
                Waiter-like tone: Maintain a friendly, helpful, and courteous tone, just like a real waiter in a restaurant would.
                
                ALWAYS ANSWER IN ITALIAN
            """
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
            """
                You are a polite, professional, and friendly virtual waiter, responsible for assisting customers with their orders. Your goal is to clearly present the customer's order, inform them of the total amount due, and politely ask if the customer want to confirm the order or change something.
                The input will be a JSON object containing the following fields:
                food_order: A list of dishes ordered by the customer.
                total: The total amount to be paid in euros.
                customer_name: The name of the customer.
                """
            f"{self._generate_base_message()}\n"
            """
                Behavior Instructions
                Order summary: Clearly list the ordered dishes from the food_order field.
                Total amount due: Inform the customer of the total price (total).
                Waiter-like tone: Maintain a friendly, helpful, and courteous tone, just like a real waiter in a restaurant would.
                
                ALWAYS ANSWER IN ITALIAN
            """

        )
        return {"output": f"{self.cat.llm(prompt)}"}

    # Handle incomplete form inputs with a nudge
    def message_incomplete(self):
        self.cat.send_ws_message("MESSAGE INCOMPLETE  FUNCTION")
        print(self._generate_base_message())
        prompt = (
            """
                You are a polite, professional, and friendly virtual waiter, responsible for assisting customers with their orders. Your goal is to clearly present the customer's order, inform them of the total amount due, and politely ask for any missing information.
                The input will be a JSON object containing the following fields:
                food_order: A list of dishes ordered by the customer.
                total: The total amount to be paid in euros.
                missing_fields: A list of missing pieces of information that need to be requested from the customer.
            """
            f"{self._generate_base_message()}\n"
            """
                Behavior Instructions
                Warm and polite greeting: Always start with a cordial greeting.
                Order summary: Clearly list the ordered dishes from the food_order field.
                Total amount due: Inform the customer of the total price (total).
                Request for missing information: Politely ask the customer to provide the missing details specified in missing_fields.
                Waiter-like tone: Maintain a friendly, helpful, and courteous tone, just like a real waiter in a restaurant would.
                
                ALWAYS ANSWER IN ITALIAN
            """
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    def update(self):
        # Conversation to JSON
        self.cat.send_ws_message("UPDATE FUNCTION")

        #EXTRACT
        json_details = self.extract()   #{'food_order': ['margherita'], 'customer_name': None, 'notes': None, 'total': 0}

        #UPDATE TOTAL
        lista_ordinato = json_details.get('food_order', [])
        tot = 0
        for elem in lista_ordinato:
            tot += get_price_of_item_in_menu(elem)
        json_details['total'] = tot

        #json_details['confirmed'] = False

        json_details = self.sanitize(json_details)     #{'food_order': ['margherita']}
        print("JSON DETAILS AFTER SANITIZE:")
        print(json_details)

        # model merge old and new
        new_model = self._model | json_details         #{'food_order': ['margherita']}
        print("NEW MODEL: ")
        print(new_model)

        # Validate new_details
        new_model = self.validate(new_model)           #{'food_order': ['margherita'], 'customer_name': None, 'notes': None}
        print("NEW MODEL AFTER VALIDATE: ")
        print(new_model)

        return new_model

    # Check user confirm the form data
    def confirm(self) -> bool:
        # Get user message
        user_message = self.cat.working_memory.user_message_json.text

        # Confirm prompt
        confirm_prompt = f"""
        ALWAYS ANSWER IN ITALIAN
        
        Your task is to produce a JSON representing whether a user is confirming or not.
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