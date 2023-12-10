
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging
import uuid
import requests

class PromptCreate():
    
    #testing function using requests librabry from command line:
    # r = requests.get("http://localhost:7071/api/player_create", json={"text": "test55", "username": "danny"})

    def __init__(self, endpoint, key, database_name, player, prompt, endpoint_translater, key_translater, location):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_player = self.database.get_container_client(player)
        self.container_prompt = self.database.get_container_client(prompt)
        self.key_translater = key_translater
        self.endpoint_translater = endpoint_translater
        self.location = location

    def getClient(self):
        return self.client

    def prompt_create(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()

            username = json_data.get("username")
            text = json_data.get("text")

            if not (15 < len(text) < 80):
                return getDump("Prompt less than 15 characters or more than 80 characters", False, 400)

            path = "/translate"
            construected_url= self.endpoint_translater + path

            # Check if the username exists in player container
            player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)

            query_username = f"SELECT * FROM c WHERE c.username = '{username}'"
            results_username = list(player_client.query_items(query_username, enable_cross_partition_query=True))

            if not results_username:
                return getDump("Player does not exist", False, 401)

            #Get user from prompt container, should already be registered
            prompt_client = self.client.get_database_client(self.database_name).get_container_client(self.container_prompt)
            results_username_prompt = list(prompt_client.query_items(query_username, enable_cross_partition_query=True))
            existing_user = results_username_prompt[0]

            #Check text provided and translate it
            params = {
                'api-version': '3.0',
                'to': ['en', 'es', 'it', 'sv', 'ru', 'id', 'bg', 'zh-Hans']
            }

            headers = {
                'Ocp-Apim-Subscription-Key': self.key_translater,
                # location required if you're using a multi-service or regional (not global) resource.
                'Ocp-Apim-Subscription-Region': self.location,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }

            body = [ { 'text': text } ]
            request = requests.post(construected_url, params=params, headers=headers, json=body)
            response = request.json()
            translations = response[0]["translations"]

            #Check the accuracy score
            language_score = response[0]["detectedLanguage"]["score"]
            if language_score < 0.3:
                return getDump("Unsupported language", False, 422)

            #Iterate through all translated texts and add to database prompt container
            new_entries = []
            for language_text_pair in translations:
                new_entries.append({ "language": language_text_pair["to"], "text": language_text_pair["text"]})

            existing_user["texts"].append(new_entries)
            prompt_client.upsert_item(existing_user)

            return getDump("OK", True, 200)

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            return func.HttpResponse(json.dumps({"result": False, "msg": "An error occurred", "error": str(e)}),
                                     mimetype="application/json",
                                     status_code=500)

def getDump(m: str, b: bool, status: int) -> func.HttpResponse:
    return func.HttpResponse(json.dumps({"result": b, "msg": m}),
                             mimetype="application/json",
                             status_code=status)

def main(req: func.HttpRequest) -> func.HttpResponse:
    endpoint = "https://quiplashy.documents.azure.com:443/"
    key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw=="

    key_translater =  "c17da301f1534fb78e4bc79cbcb3ece4"
    endpoint_translater = "https://api.cognitive.microsofttranslator.com/"
    location = "uksouth"

    database_name = "quiplash"
    player = "player"
    prompt = "prompt"

    obj = PromptCreate(endpoint, key, database_name, player, prompt, endpoint_translater, key_translater, location)
    return obj.prompt_create(req)
