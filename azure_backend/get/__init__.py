from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging

class Get():

    def __init__(self, endpoint, key, database_name, prompt):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_prompt = self.database.get_container_client(prompt)

    def get(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()

            usernames = json_data.get("players")
            language = json_data.get("language")

            #Go through each user and retrieve matched texts
            #TODO:Improve O(n^3) algorithm for getting language matched texts - for the sake of time this will do
            tmp = []
            for user in usernames:
                query_username = f"SELECT * FROM c WHERE c.username = '{user}'"
                prompt_client = self.client.get_database_client(self.database_name).get_container_client(self.container_prompt)
                results = list(prompt_client.query_items(query_username, enable_cross_partition_query=True))

                user_id = results[0]["id"]
                user_username = results[0]["username"]
                user_texts = results[0]["texts"]
            
                #METOD 1: return each instance in a list for each instance of a user

                #language_matched = []
                #for text_entry in user_texts:
                #    language_matched.append([text["text"] for text in text_entry if text["language"] == language][0])
                #tmp.append({ "id": user_id, "text": language_matched, "username": user_username })

                #METOD 2: return each instance in its own JSON string 
                for text_entry in user_texts:
                    language_matched = ([text["text"] for text in text_entry if text["language"] == language][0])
                    tmp.append({ "id": user_id, "text": language_matched, "username": user_username })
                
            return func.HttpResponse(json.dumps(tmp), mimetype="application/json", status_code=200)

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

    database_name = "quiplash"
    prompt = "prompt"

    obj = Get(endpoint, key, database_name, prompt)
    return obj.get(req)

#{ "players": ["danny", "alba"], "language": "en" }