from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging


class PlayerLoggin():

    def __init__(self, endpoint, key, database_name, player, prompt):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_player = self.database.get_container_client(player)
        self.container_prompt = self.database.get_container_client(prompt)
    
    def getClient(self):
        return self.client

    def player_login(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()

            if "username" not in json_data or "password" not in json_data:
                return getDump("Username or password not provided", False, 400)

            username = json_data.get("username")
            password = json_data.get("password")

            # Check if the username exists
            player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)

            query_username = f"SELECT * FROM c WHERE c.username = '{username}'"
            results_username = list(player_client.query_items(query_username, enable_cross_partition_query=True))

            if not results_username:
                return getDump("Username or password incorrect", False, 401)

            # Check if the username has the correct password
            password_real = results_username[0].get("password")

            if password_real == password:
                return getDump("OK", True, 200)
            else:
                return getDump("Username or password incorrect", False, 401)

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
    player = "player"
    prompt = "prompt"

    obj = PlayerLoggin(endpoint, key, database_name, player, prompt)
    return obj.player_login(req)