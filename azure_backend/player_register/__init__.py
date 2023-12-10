from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging
import uuid


class PlayerRegistration():

    #testing function using requests librabry from command line:
    # r = requests.get("http://localhost:7071/player/register/", json={"username": "danny", "password": "mypasgt"})

    def __init__(self, endpoint, key, database_name, player, prompt):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_player = self.database.get_container_client(player)
        self.container_prompt = self.database.get_container_client(prompt)

    def getClient(self):
        return self.client

    def player_register(self, req: func.HttpRequest) -> func.HttpResponse:
        try:

            json_data = req.get_json()


            if "username" not in json_data or "password" not in json_data:
                return getDump("Username or password not provided", False, 400)

            username = json_data.get("username")
            password = json_data.get("password")

            if not (4 <= len(username) <= 14):
                return getDump("Username less than 4 characters or more than 14 characters", False, 400)

            if not (10 <= len(password) <= 20):
                return getDump("Password less than 10 characters or more than 20 characters", False, 400)

            # Check if the username already exists
            player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)
            query = f"SELECT * FROM c WHERE c.username = '{username}'"
            results = list(player_client.query_items(query, enable_cross_partition_query=True))

            if len(results) > 0:
                return getDump("Username already exists", False, 409)

            # Register the player
            player_item = {
                "id": str(uuid.uuid4()),
                "username": username,
                "password": password,
                "games_played": 0,
                "total_score": 0
            }
            player_client.create_item(player_item)

            # Register the player's prompt
            prompt_client = self.client.get_database_client(self.database_name).get_container_client(self.container_prompt)
            prompt_item = {
                "id": str(uuid.uuid4()),
                "username": username,
                "texts": []
            }
            prompt_client.create_item(prompt_item)

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

    database_name = "quiplash"
    player = "player"
    prompt = "prompt"

    obj = PlayerRegistration(endpoint, key, database_name, player, prompt)
    return obj.player_register(req)