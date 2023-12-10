from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging


class PlayerUpdate():

    def __init__(self, endpoint, key, database_name, player, prompt):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_player = self.database.get_container_client(player)
        self.container_prompt = self.database.get_container_client(prompt)

    def getClient(self):
        return self.client

    def player_update(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()

            if "username" not in json_data or "password" not in json_data:
                return getDump("Username or password not provided", False, 400)

            username = json_data.get("username")
            password = json_data.get("password")
            games_played = json_data.get("add_to_games_played")
            score = json_data.get("add_to_score")

            # Check if the username exists
            player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)

            query_username = f"SELECT * FROM c WHERE c.username = '{username}'"
            results_username = list(player_client.query_items(query_username, enable_cross_partition_query=True))

            if not results_username:
                return getDump("Player does not exist", False, 401)

            # Check if the username has the correct password
            password_real = results_username[0].get("password")

            #Username already checked, if password is correct, find user in database
            if password_real == password:
                player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)
                query = f"SELECT * FROM c WHERE c.username = '{username}' AND c.password = '{password}'"
                results = list(player_client.query_items(query, enable_cross_partition_query=True))

                if results: 
                    tmp = results[0]

                    current_games_played = tmp["games_played"]
                    new_games_played = current_games_played + games_played
                    tmp["games_played"] = new_games_played
                    self.container_player.replace_item(item=tmp, body=tmp)

                    current_score = tmp["total_score"]
                    new_score = current_score + score
                    tmp["total_score"] = new_score
                    self.container_player.replace_item(item=tmp, body=tmp)

                else:
                    return getDump("Details not found for player", False, 401)
                
                return getDump("OK", True, 200)
            else:
                return getDump("Player does not exist", False, 401)

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

    obj = PlayerUpdate(endpoint, key, database_name, player, prompt)
    return obj.player_update(req)

# {"username": "danny" , "password": "password123" , "add_to_games_played": 66, "add_to_score" : 77}