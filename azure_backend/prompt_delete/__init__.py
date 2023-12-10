from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging

class PromptDelete():

    def __init__(self, endpoint, key, database_name, prompt):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_prompt = self.database.get_container_client(prompt)

    def getClient(self):
        return self.client

    def prompt_delete(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()

            username = json_data.get("player")
            if username:
                #Get user from prompt container, should already be registered
                query_username = f"SELECT * FROM c WHERE c.username = '{username}'"
                prompt_client = self.client.get_database_client(self.database_name).get_container_client(self.container_prompt)
                results_username_prompt = list(prompt_client.query_items(query_username, enable_cross_partition_query=True))


                user_texts = results_username_prompt[0]
                all_texts = len(user_texts["texts"]) 
                user_texts["texts"] = []
                prompt_client.replace_item(item=user_texts, body=user_texts)
            
                return getDump(f"{all_texts} prompts deleted", True, 200)

            word = json_data.get("word")
            if word:
                results = self.container_prompt.query_items(
                    query='SELECT * FROM c',
                    enable_cross_partition_query=True
                )

                # Filter texts and keep only those that don't contain the keyword
                # Improve n(O^2) time complexity for this 
                for result in results:
                    texts = result.get("texts", [])

                    texts_n = len(texts)                

                    filtered_texts = [
                        text for text in texts if word not in text[0]["text"]
                    ]

                    result["texts"] = filtered_texts
                    texts_n_updated = len(filtered_texts)
                    self.container_prompt.upsert_item(result)

                #Just calculate the difference between the original and current size of the array to get the total prompts deleted
                return getDump(f"{texts_n - texts_n_updated} prompts deleted", True, 200)

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

    obj = PromptDelete(endpoin^2t, key, database_name, prompt)
    return obj.prompt_create(req)

#{ "player": "danny" } or { "word": "boom" }