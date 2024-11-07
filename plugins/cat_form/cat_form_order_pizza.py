from cat.mad_hatter.decorators import tool, hook
from pydantic import Field, field_validator
from cat.log import log
from typing import Dict
from .cform import CForm, CBaseModel
import json
import random

menu = [ "Margherita", "Romana", "Quattro Formaggi", "Capricciosa", "Bufalina", "Diavola"]
    

# Declare model class
class PizzaOrder(CBaseModel):
    
    pizza_type: str = Field(
        #default = None,
        description = "The type of pizza",
        examples = [
            ("I would like a Capricciosa pizza,", "Capricciosa"),
            ("Margherita is my favorite", "Margherita")
        ])
    
    address: str = Field(
        #default = None,
        description = "The user's address",
        examples = [
            ("My address is via Libertà 21 in Rome,", "via Libertà 21, Rome"),
            ("I live in Corso Italia 34", "Corso Italia 34")
        ])
    
    phone: str = Field(
        #default = None,
        description = "The user's telephone number",
        examples = [
            ("033234534 ", "033234534"),
            ("my number is 08234453", "08234453"),
            ("For any communications 567493423", "567493423")
        ])

    @field_validator("pizza_type")
    @classmethod
    def validate_pizza_type(cls, pizza_type: str):
        log.critical(f"Validating pizza type: {pizza_type}")
        if pizza_type not in [None, ""] and pizza_type not in list(menu):
            raise ValueError(f"pizza_type {pizza_type} is not present in the menu")

        return

    def examples(self, cat):
        settings = cat.mad_hatter.get_plugin().load_settings()
        return json.loads(settings["pizza_order_examples"])

    def execute_action(self, cat):
        result = "<h3>PIZZA CHALLENGE - ORDER COMPLETED<h3><br>" 
        result += "<table border=0>"
        result += "<tr>"
        result += "   <td>Pizza Type</td>"
        result += f"  <td>{self.pizza_type}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Address</td>"
        result += f"  <td>{self.address}</td>"
        result += "</tr>"
        result += "<tr>"
        result += "   <td>Phone Number</td>"
        result += f"  <td>{self.phone}</td>"
        result += "</tr>"
        result += "</table>"
        result += "<br>"                                                                                                     
        result += "Thanks for your order.. your pizza is on its way!"
        result += "<br><br>"
        result += f"<img style='width:400px' src='https://maxdam.github.io/cat-pizza-challenge/img/order/pizza{random.randint(0, 6)}.jpg'>"
        return result


# Extend CForm class
class MyForm(CForm):
    def __init__(self, model_class, key, cat):
        print("MyForm constructor")
        super().__init__(model_class, key, cat)
    
    def check_user_confirm(self) -> bool:
        print("MyForm check_user_confirm")
        return super().check_user_confirm() 
    
    def user_message_to_json(self):
        print("MyForm user_message_to_json")
        return super().user_message_to_json()
    
    def model_merge(self, json_details):
        print("MyForm model_merge")
        return super().model_merge(json_details)
        
    def model_validate(self, model):
        print("MyForm model_validate")
        return super().model_validate(model)
    


# Order pizza start intent
@tool(return_direct=True)
def start_order_pizza_intent(input, cat):
    """I would like to order a pizza
    I'll take a Margherita pizza"""
    log.critical("INTENT ORDER PIZZA START")
    return PizzaOrder.start(cat, form=MyForm)

 
# Order pizza stop intent
@tool
def stop_order_pizza_intent(input, cat):
    """I don't want to order pizza anymore, 
    I want to give up on the order, 
    go back to normal conversation"""
    log.critical("INTENT ORDER PIZZA STOP")
    return PizzaOrder.stop(cat)

# Get pizza menu
@tool()
def ask_menu(input, cat):
    """What is on the menu?
    Which types of pizza do you have?"""
    log.critical("INTENT ORDER PIZZA MENU")
    response = "The available pizzas are the following:\n" + ", ".join(menu)
    return response


'''
# Order pizza handle conversation
@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    return PizzaOrder.dialogue(fast_reply, cat)

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    return PizzaOrder.dialogue_prompt(prefix, cat)
'''
