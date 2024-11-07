from pydantic import ValidationError, BaseModel
from cat.mad_hatter.decorators import hook
from cat.looking_glass.prompts import MAIN_PROMPT_PREFIX, MAIN_PROMPT_SUFFIX
from cat.log import log
from typing import Dict
from enum import Enum
import json

from qdrant_client.http.models import Distance, VectorParams, PointStruct

from langchain.prompts.prompt import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
import guardrails as gd #https://www.guardrailsai.com/docs/guardrails_ai/getting_started
from kor import create_extraction_chain, from_pydantic #https://github.com/eyurtsev/kor

from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain.vectorstores import Qdrant


   

# Conversational Form State
class CFormState(Enum):
    INVALID         = 0
    VALID           = 1
    WAIT_CONFIRM    = 2
    UPDATE          = 3


# Class Conversational Form
class CForm():

    def __init__(self, model_class, key, cat):
        self.state = CFormState.INVALID
        self.model_class = model_class
        self.model = model_class.model_construct()
        self.key   = key
        self.cat   = cat
        
        self.is_valid = False
        self.errors  = []
        self.ask_for = []

        self.prompt_tpl_update   = None
        self.prompt_tpl_response = None
        self.load_dialog_examples_by_rag()
        self.load_confirm_examples_by_rag()
        self.load_exit_intent_examples_by_rag()
        
        self.language = self.get_language()


    ####################################
    ######## HANDLE ACTIVE FORM ########
    ####################################

    # Check that there is only one active form
    def check_active_form(self):
        if "_active_cforms" not in self.cat.working_memory.keys():
            self.cat.working_memory["_active_cforms"] = []
        if self.key not in self.cat.working_memory["_active_cforms"]:
            self.cat.working_memory["_active_cforms"].append(self.key)
        for key in self.cat.working_memory["_active_cforms"]:
            if key != self.key:
                self.cat.working_memory["_active_cforms"].remove(key)
                if key in self.cat.working_memory.keys():
                    del self.cat.working_memory[key]

    # Class method get active form
    @classmethod
    def get_active_form(cls, cat):
        if "_active_cforms" in cat.working_memory.keys():
            key = cat.working_memory["_active_cforms"][0]
            if key in cat.working_memory.keys():
                cform = cat.working_memory[key]
                return cform
        return None


    ##########################
    ######## LANGUAGE ########
    ##########################

    # Get language
    def get_language(self):

        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]

        # Prompt
        language_prompt = f"Identify the language of the following message \
        and return only the language of the message, without other text.\n\
        If you can't locate it, return 'English'.\n\
        Message examples:\n\
        'Ciao, come stai?', returns: 'Italian',\n\
        'How do you go?', returns 'English',\n\
        'Bonjour a tous', returns 'French'\n\n\
        Message: '{user_message}'"
        
        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(language_prompt)
        log.critical(f'Language: {response}')
        return response
    

    ####################################
    ######## CHECK USER CONFIRM ########
    ####################################
        
    # Check user confirm the form data
    def check_user_confirm(self) -> bool:
        
        # Decides whether to use rag for user confirmation
        settings = self.cat.mad_hatter.get_plugin().load_settings()
        if settings["use_rag_confirm"] is True:
            return self.check_user_confirm_rag()

        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Confirm prompt
        confirm_prompt = f"Given a sentence that I will now give you,\n\
        just respond with 'YES' or 'NO' depending on whether the sentence is:\n\
        - a refusal either has a negative meaning or is an intention to cancel the form (NO)\n\
        - an acceptance has a positive or neutral meaning (YES).\n\
        If you are unsure, answer 'NO'.\n\n\
        The sentence is as follows:\n\
        User message: {user_message}"
        
        # Print confirm prompt
        print("*"*10)
        print("CONFIRM PROMPT:")
        print(confirm_prompt)
        print("*"*10)

        # Queries the LLM and check if user is agree or not
        response = self.cat.llm(confirm_prompt)
        log.critical(f'check_user_confirm: {response}')
        confirm = "NO" not in response and "YES" in response
        
        print("RESPONSE: " + str(confirm))
        return confirm
    

    # Load confirm examples by RAG
    def load_confirm_examples_by_rag(self):
        
        qclient = self.cat.memory.vectors.vector_db
        self.confirm_collection = "user_confirm"
        
        # Get embedder size
        embedder_size = len(self.cat.embedder.embed_query("hello world"))

        # Create collection
        qclient.recreate_collection(
            collection_name=self.confirm_collection,
            vectors_config=VectorParams(
                size=embedder_size, 
                distance=Distance.COSINE
            )
        )

        # Load context
        examples = [ 
            {"message": "yes, they are correct",   "label": "True" },
            {"message": "ok, they are fine",       "label": "True" },
            {"message": "they seem right",         "label": "True" },
            {"message": "I think so",              "label": "True" },
            {"message": "no, we are not there",    "label": "False"},
            {"message": "wrong",                   "label": "False"},
            {"message": "they are not correct",    "label": "False"},
            {"message": "I don't think so",        "label": "False"}
        ]

        # Insert training data into index
        points = []
        for i, data in enumerate(examples):
            message = data["message"]
            label = data["label"]
            vector = self.cat.embedder.embed_query(message)
            points.append(PointStruct(id=i, vector=vector, payload={"label":label}))
            
        operation_info = qclient.upsert(
            collection_name=self.confirm_collection,
            wait=True,
            points=points,
        )
        #print(operation_info)


    # Check if user confirm the model data in RAG mode
    def check_user_confirm_rag(self) -> bool:
        
        # Get user message vector
        user_message = self.cat.working_memory["user_message_json"]["text"]
        user_message_vector = self.cat.embedder.embed_query(user_message)
        
        # Search for the vector most similar to the user message in the vector database
        qclient = self.cat.memory.vectors.vector_db
        search_results = qclient.search(
            self.confirm_collection, 
            user_message_vector, 
            with_payload=True, 
            limit=1
        )
        print(f"search_results: {search_results}")
        most_similar_label = search_results[0].payload["label"]
        
        # If the nearest distance is less than the threshold, exit intent
        return most_similar_label == "True"
    

    ###################################
    ######## CHECK EXIT INTENT ########
    ###################################

    # Load exit intent examples
    def load_exit_intent_examples_by_rag(self):
        
        qclient = self.cat.memory.vectors.vector_db
        self.exit_intent_collection = "exit_intent"
        
        # Get embedder size
        embedder_size = len(self.cat.embedder.embed_query("hello world"))

        # Create collection
        qclient.recreate_collection(
            collection_name=self.exit_intent_collection,
            vectors_config=VectorParams(
                size=embedder_size, 
                distance=Distance.COSINE
            )
        )
        
        # Load context
        examples = [ 
            {"message": "I would like to exit the module"                   },
            {"message": "I no longer want to continue filling out the form" },
            {"message": "You go out"                                        },
            {"message": "Return to normal conversation"                     },
            {"message": "Stop and go out"                                   }
        ]

        # Insert training data into index
        points = []
        for i, data in enumerate(examples):
            message = data["message"]
            vector = self.cat.embedder.embed_query(message)
            points.append(PointStruct(id=i, vector=vector, payload={}))
            
        operation_info = qclient.upsert(
            collection_name=self.exit_intent_collection,
            wait=True,
            points=points,
        )
        #print(operation_info)


    # Check if the user wants to exit the intent
    def check_exit_intent_rag(self) -> bool:
        
        # Get user message vector
        user_message = self.cat.working_memory["user_message_json"]["text"]
        user_message_vector = self.cat.embedder.embed_query(user_message)
        
        # Search for the vector most similar to the user message in the vector database and get distance
        qclient = self.cat.memory.vectors.vector_db
        search_results = qclient.search(
            self.exit_intent_collection, 
            user_message_vector, 
            with_payload=False, 
            limit=1
        )
        print(f"search_results: {search_results}")
        nearest_score = search_results[0].score
        
        # If the nearest score is less than the threshold, exit intent
        threshold = 0.9
        return nearest_score >= threshold


    ####################################
    ############ UPDATE JSON ###########
    ####################################

    # Updates the form with the information extracted from the user's response
    # (Return True if the model is updated)
    def update(self):

        # User message to json details
        json_details = self.user_message_to_json()
        if json_details is None:
            return False
        
        # model merge with details
        print("json_details", json_details)
        new_model = self.model_merge(json_details)
        print("new_model", new_model)
        
        # Check if there is no information in the new_model that can update the form
        if new_model == self.model.model_dump():
            return False

        # Validate new_details
        self.model_validate(new_model)
                    
        # If there are errors, return false
        if len(self.errors) > 0:
            return False

        # Overrides the current model with the new_model
        self.model = self.model.model_construct(**new_model)

        log.critical(f'MODEL : {self.model.model_dump()}')
        return True


    # User message to json
    def user_message_to_json(self): 
        settings = self.cat.mad_hatter.get_plugin().load_settings()

        # Extract json detail from user message, based on the json_extractor setting

        if settings["json_extractor"] == "langchain":
            json_details = self._extract_info_by_langchain()
                
        if settings["json_extractor"] == "kor":
            json_details = self._extract_info_by_kor()
                    
        if settings["json_extractor"] == "guardrails":
            json_details = self._extract_info_by_guardrails()
                        
        if settings["json_extractor"] == "from examples":
            json_details = self._extract_info_from_examples_by_rag()

        return json_details


    # Model merge (actual model + details = new model)
    def model_merge(self, json_details):
        # Clean json details
        json_details = {key: value for key, value in json_details.items() if value not in [None, '', 'None', 'null', 'lower-case']}

        # update form
        new_model = self.model.model_dump() | json_details
        
        # Clean json new_details
        new_model = {key: value for key, value in new_model.items() if value not in [None]}        
        return new_model


    # Validate model
    def model_validate(self, model):
        self.ask_for = []
        self.errors  = []

        # Reset state to INVALID
        self.state = CFormState.INVALID
                
        try:
            # Pydantic model validate
            self.model.model_validate(model)

            # If model is valid change state to VALID
            self.state = CFormState.VALID

        except ValidationError as e:
            
            # Collect ask_for and errors messages
            for error_message in e.errors():
                if error_message['type'] == 'missing':
                    self.ask_for.append(error_message['loc'][0])
                else:
                    self.errors.append(error_message["msg"])


    #############################################
    ############ USER MESSAGE TO JSON ###########
    #############################################

    # Extracted new informations from the user's response (by pydantic langchain - pydantic library)
    def _extract_info_by_langchain(self):
        parser = PydanticOutputParser(pydantic_object=type(self.model))
        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        log.debug(f'get_format_instructions: {parser.get_format_instructions()}')
        
        user_message = self.cat.working_memory["user_message_json"]["text"]
        _input = prompt.format_prompt(query=user_message)
        output = self.cat.llm(_input.to_string())
        log.debug(f"output: {output}")

        user_response_json = json.loads(output)
        log.debug(f'user response json: {user_response_json}')
        return user_response_json
    

    # Extracted new informations from the user's response (by kor library)
    def _extract_info_by_kor(self):

        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Get schema and validator from Pydantic model
        schema, validator = from_pydantic(self.model_class)   
        chain = create_extraction_chain(
            self.cat._llm, 
            schema, 
            encoder_or_encoder_class="json", 
            validator=validator
        )
        log.debug(f"prompt: {chain.prompt.to_string(user_message)}")
        
        output = chain.run(user_message)["validated_data"]
        try:
            user_response_json = output.dict()
            log.debug(f'user response json: {user_response_json}')
            return user_response_json
        except Exception  as e:
            log.debug(f"An error occurred: {e}")
            return None
    

    # Extracted new informations from the user's response (by guardrails library)
    def _extract_info_by_guardrails(self):
        
        # Get user message
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        # Prompt
        prompt = """
        Given the following client message, please extract information about his form.

        ${message}

        ${gr.complete_json_suffix_v2}
        """
        
        # Parse message
        guard = gd.Guard.from_pydantic(output_class=self.model_class, prompt=prompt)
        gd_result = guard(self.cat._llm, prompt_params={"message": user_message})
        print(f'gd_result: {gd_result}')

        # If result is valid, return result
        if gd_result.validation_passed is True:
            result = json.loads(gd_result.raw_llm_output)
            print(f'_extract_info: {user_message} -> {result}')
            return result
        
        return {}

    # Extracted new informations from the user's response (from examples, by rag)
    def _extract_info_from_examples_by_rag(self):
        user_message = self.cat.working_memory["user_message_json"]["text"]
        
        prompt = "Update the following JSON with information extracted from the Sentence:\n\n"
        
        if self.prompt_tpl_update:
            prompt += self.prompt_tpl_update.format(
                user_message = user_message, 
                model = self.model.model_dump_json()
            )
        else:
            prompt += f"\
                Sentence: {user_message}\n\
                JSON:{json.dumps(self.model.dict(), indent=4)}\n\
                Updated JSON:"
            
        json_str = self.cat.llm(prompt)
        print(f"json after parser: {json_str}")
        user_response_json = json.loads(json_str)
        return user_response_json
    
    
    # Load dialog examples by RAG
    def load_dialog_examples_by_rag(self):    
        '''
        # Examples json format
        self.model.examples = [
            {
                "user_message": "I want to order a pizza",
                "model_before": "{{}}",
                "model_after":  "{{}}",
                "validation":   "information to ask: pizza type, address, phone",
                "response":     "What kind of pizza do you want?"
            },
            {
                "user_message": "I live in Via Roma 1",
                "model_before": "{{\"pizza_type\":\"Margherita\"}}",
                "model_after":  "{{\"pizza_type\":\"Margherita\",\"address\":\"Via Roma 1\"}}",
                "validation":   "information to ask: phone",
                "response":     "Could you give me your phone number?"
            },
            {
                "user_message": "My phone is: 123123123",
                "model_before": "{{\"pizza_type\":\"Diavola\"}}",
                "model_after":  "{{\"pizza_type\":\"Diavola\",\"phone\":\"123123123\"}}",
                "validation":   "information to ask: address",
                "response":     "Could you give me your delivery address?"
            },
            {
                "user_message": "I want a test pizza",
                "model_before": "{{\"phone\":\"123123123\"}}",
                "model_after":  "{{\"pizza_type\":\"test\", \"phone\":\"123123123\"}}",
                "validation":   "there is an error: pizza_type test is not present in the menu",
                "response":     "Pizza type is not a valid pizza"
            }
        ]
        '''

        # Get examples
        examples = self.model.examples(self.cat)
        #print(f"examples: {examples}")

        # If no examples are available, return
        if not examples:
            return
        
        # Create example selector
        example_selector = SemanticSimilarityExampleSelector.from_examples(
            examples, self.cat.embedder, Qdrant, k=1, location=':memory:'
        )

        # Create example_update_model_prompt for formatting output
        example_update_model_prompt = PromptTemplate(
            input_variables = ["user_message", "model_before", "model_after"],
            template = "User Message: {user_message}\nModel: {model_before}\nUpdated Model: {model_after}"
        )
        #print(f"example_update_model_prompt:\n{example_update_model_prompt.format(**examples[1])}\n\n")

        # Create promptTemplate from examples_selector and example_update_model_prompt
        self.prompt_tpl_update = FewShotPromptTemplate(
            example_selector = example_selector,
            example_prompt   = example_update_model_prompt,
            suffix = "User Message: {user_message}\nModel: {model}\nUpdated Model: ",
            input_variables = ["user_message", "model"]
        )
        #print(f"prompt_tpl_update: {self.prompt_tpl_update.format(user_message='user question', model=self.model.model_dump_json())}\n\n")

        # Create example_response_prompt for formatting output
        example_response_prompt = PromptTemplate(
            input_variables = ["validation", "response"],
            template = "Message: {validation}\nResponse: {response}"
        )
        #print(f"example_response_prompt:\n{example_response_prompt.format(**examples[1])}\n\n")

        # Create promptTemplate from examples_selector and example_response_prompt
        self.prompt_tpl_response = FewShotPromptTemplate(
            example_selector = example_selector,
            example_prompt   = example_response_prompt,
            suffix = "Message: {validation}\nResponse: ",
            input_variables = ["validation"]
        )
        #print(f"prompt_tpl_response: {self.prompt_tpl_response.format(validation='pydantic validation result')}\n\n")


    ####################################
    ######### EXECUTE DIALOGUE #########
    ####################################
    
    # Execute the dialogue step
    def dialogue(self):
        # Get settings
        settings = self.cat.mad_hatter.get_plugin().load_settings()

        # Based on the strict setting it decides whether to use a direct dialogue or involve the memory chain 
        if settings["strict"] is True:
            return self.dialogue_direct()
        else:
            return self.dialogue_action()


    # Execute the dialogue action
    def dialogue_action(self):
        log.critical(f"dialogue_action (state: {self.state})")

        #self.cat.working_memory["episodic_memories"] = []

        # Get settings
        settings = self.cat.mad_hatter.get_plugin().load_settings()
        
        # If the state is INVALID or UPDATE, execute model update (and change state based on validation result)
        if self.state in [CFormState.INVALID, CFormState.UPDATE]:
            self.update()
            log.warning("> UPDATE")

        # If state is VALID, ask confirm (or execute action directly)
        if self.state in [CFormState.VALID]:
            if settings["ask_confirm"] is False:
                log.warning("> EXECUTE ACTION")
                del self.cat.working_memory[self.key]   
                return self.model.execute_action(self.cat)
            else:
                self.state = CFormState.WAIT_CONFIRM
                log.warning("> STATE=WAIT_CONFIRM")
                return None
            
        # If state is WAIT_CONFIRM, check user confirm response..
        if self.state in [CFormState.WAIT_CONFIRM]:
            if self.check_user_confirm():
                log.warning("> EXECUTE ACTION")
                del self.cat.working_memory[self.key]   
                return self.model.execute_action(self.cat)
            else:
                log.warning("> STATE=UPDATE")
                self.state = CFormState.UPDATE
                return None

        return None
    

    # execute dialog prompt prefix
    def dialogue_prompt(self, prompt_prefix):
        log.critical(f"dialogue_prompt (state: {self.state})")

        # Get class fields descriptions
        class_descriptions = []
        for key, value in self.model_class.model_fields.items():
            class_descriptions.append(f"{key}: {value.description}")
        
        # Formatted texts
        formatted_model_class = ", ".join(class_descriptions)
        formatted_model       = ", ".join([f"{key}: {value}" for key, value in self.model.model_dump().items()])
        formatted_ask_for     = ", ".join(self.ask_for) if self.ask_for else None
        formatted_errors      = ", ".join(self.errors) if self.errors else None
        
        formatted_validation  = ""
        if self.ask_for:
            formatted_validation  = f"information to ask: {formatted_ask_for}"
        if self.errors:
            formatted_validation  = f"there is an error: {formatted_errors}"

        prompt = prompt_prefix

        # If state is INVALID ask missing informations..
        if self.state in [CFormState.INVALID]:
            # PROMPT ASK MISSING INFO
            prompt = \
                f"Your goal is to have the user fill out a form containing the following fields:\n\
                {formatted_model_class}\n\n\
                you have currently collected the following values:\n\
                {formatted_model}\n\n"

            if self.errors:
                prompt += \
                    f"and in the validation you got the following errors:\n\
                    {formatted_errors}\n\n"

            if self.ask_for:    
                prompt += \
                    f"and the following fields are still missing:\n\
                    {formatted_ask_for}\n\n"

            prompt += \
                f"ask the user to give you the necessary information."
            
            if self.prompt_tpl_response:
                prompt += "\n\n" + self.prompt_tpl_response.format(validation = formatted_validation)
                
        # If state is WAIT_CONFIRM (previous VALID), show summary and ask the user for confirmation..
        if self.state in [CFormState.WAIT_CONFIRM]:
            # PROMPT SHOW SUMMARY
            prompt = f"Your goal is to have the user fill out a form containing the following fields:\n\
                {formatted_model_class}\n\n\
                you have collected all the available data:\n\
                {formatted_model}\n\n\
                show the user the data and ask them to confirm that it is correct.\n"

        # If state is UPDATE asks the user to change some information present in the model..
        if self.state in [CFormState.UPDATE]:
            # PROMPT ASK CHANGE INFO
            prompt = f"Your goal is to have the user fill out a form containing the following fields:\n\
                {formatted_model_class}\n\n\
                you have collected all the available data:\n\
                {formatted_model}\n\n\
                show the user the data and ask him to provide the updated data.\n"


        # Print prompt prefix
        print("*"*10, f"\nPROMPT PREFIX:\n{prompt}\n", "*"*10)

        # Return prompt
        return prompt


    # execute dialog direct (combines the previous two methods)
    def dialogue_direct(self):

        # check exit intent
        if self.check_exit_intent_rag():
            log.critical(f'> Exit Intent {self.key}')
            del self.cat.working_memory[self.key]
            return None
    
        # Get dialog action
        response = self.dialogue_action()
        if not response:
            # Build prompt
            user_message = self.cat.working_memory["user_message_json"]["text"]
            prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)
            prompt_prefix = self.dialogue_prompt(prompt_prefix)
            prompt_prefix += f"\nUse the {self.language} language to answer the question.\n\n"
            prompt = f"{prompt_prefix}\n\n\
                User message: {user_message}\n\
                AI:"
            
            # Print prompt
            print("*"*10, f"\nPROMPT:\n{prompt}\n", "*"*10)

            # Call LLM
            response = self.cat.llm(prompt)

        return response
    
    
    # Execute the entire memory chain
    def execute_memory_chain(self):
        agent_input   = self.cat.agent_manager.format_agent_input(self.cat.working_memory)
        agent_input   = self.cat.mad_hatter.execute_hook("before_agent_starts", agent_input, cat=self.cat)
        agent_input["tools_output"] = ""
        prompt_prefix = self.cat.mad_hatter.execute_hook("agent_prompt_prefix", MAIN_PROMPT_PREFIX, cat=self.cat)
        prompt_prefix = self.dialogue_prompt(prompt_prefix)
        prompt_suffix = self.cat.mad_hatter.execute_hook("agent_prompt_suffix", MAIN_PROMPT_SUFFIX, cat=self.cat)
        response = self.cat.agent_manager.execute_memory_chain(agent_input, prompt_prefix, prompt_suffix, self.cat)
        return response.get("output")
    

#####################################
######### CLASS BASE MODEL ##########
#####################################

# Class Conversational Base Model
class CBaseModel(BaseModel):
    
    # Get CForm instance
    @classmethod
    def get(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            return cat.working_memory[key]
        return None
    
    # Start conversation
    # (typically inside the tool that starts the intent)
    @classmethod
    def start(cls, cat, form=CForm):
        key = cls.__name__
        if key not in cat.working_memory.keys():
            cform = form(cls, key, cat)
            cat.working_memory[key] = cform
            cform.check_active_form()
            response = cform.dialogue()
            return response
        cform = cat.working_memory[key]
        cform.check_active_form()
        response = cform.execute_memory_chain()
        return response

    # Stop conversation
    # (typically inside the tool that stops the intent)
    @classmethod
    def stop(cls, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            del cat.working_memory[key]
        return

    # Execute the dialogue step
    # (typically inside the agent_fast_reply hook)
    @classmethod
    def dialogue(cls, fast_reply, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            response = cform.dialogue()
            if response:
                return { "output": response }
        return
    
    # Execute the dialogue_prompt step
    # (typically inside the agent_prompt_prefix hook)
    @classmethod
    def dialogue_prompt(cls, prefix, cat):
        key = cls.__name__
        if key in cat.working_memory.keys():
            cform = cat.working_memory[key]
            return cform.dialogue_prompt(prefix)
        return prefix


    # METHODS TO OVERRIDE
    
    # Execute final form action
    def execute_action(self, cat):
        return self.model_dump_json(indent=4)
    
    # Dialog examples
    def examples(self, cat):
        return []
 

############################################################
######### HOOKS FOR AUTOMATIC HANDLE CONVERSATION ##########
############################################################

@hook
def agent_fast_reply(fast_reply: Dict, cat) -> Dict:
    settings = cat.mad_hatter.get_plugin().load_settings()
    if settings["auto_handle_conversation"] is True:
        cform = CForm.get_active_form(cat)
        if cform:
            return cform.model.dialogue(fast_reply, cat)
    return fast_reply

@hook
def agent_prompt_prefix(prefix, cat) -> str:
    settings = cat.mad_hatter.get_plugin().load_settings()
    if settings["auto_handle_conversation"] is True:
        cform = CForm.get_active_form(cat)
        if cform:
            return cform.model.dialogue_prompt(prefix, cat)
    return prefix
