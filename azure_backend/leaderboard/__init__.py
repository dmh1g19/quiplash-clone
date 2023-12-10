from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
import logging

class Get():

    def __init__(self, endpoint, key, database_name, player):
        self.database_name = database_name
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(self.database_name)
        self.container_player = self.database.get_container_client(player)

    def get(self, req: func.HttpRequest) -> func.HttpResponse:
        try:
            json_data = req.get_json()
            k = json_data.get("top")

            query_username = f"SELECT TOP {k} * FROM c ORDER BY c.total_score DESC, c.games_played ASC, c.username ASC"

            player_client = self.client.get_database_client(self.database_name).get_container_client(self.container_player)
            results = list(player_client.query_items(query_username, enable_cross_partition_query=True))

            player_list = []
            for player in results:
                data = {
                    "username": player["username"],
                    "games_played": player["games_played"],
                    "total_score": player["total_score"]
                }
                player_list.append(data)


            return func.HttpResponse(json.dumps(player_list), mimetype="application/json", status_code=200)

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            return func.HttpResponse(json.dumps({"result": False, "msg": "An error occurred", "error": str(e)}),
                                     mimetype="application/json",
                                     status_code=500)

def main(req: func.HttpRequest) -> func.HttpResponse:
    endpoint = "https://quiplashy.documents.azure.com:443/"
    key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw=="

    database_name = "quiplash"
    player = "player"

    obj = Get(endpoint, key, database_name, player)
    return obj.get(req)

# { "top":  3 }