import unittest
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
from player_update import PlayerUpdate 

#Asumming the database already contains an entry s.t: { "username": "Danny", "password": "mypassword" }

class test_update(unittest.TestCase):
    create_instance = PlayerUpdate(
       endpoint = "https://quiplashy.documents.azure.com:443/",
       key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw==",
       database_name = "quiplash",
       player = "player",
       prompt = "prompt"
    )

    #Empty both containers
    def tear_down(self):
        client = self.create_instance.getClient()

        player_container = client.get_database_client("quiplash").get_container_client("player")
        prompt_container = client.get_database_client("quiplash").get_container_client("prompt")

        player_items = player_container.read_all_items()
        prompt_items = prompt_container.read_all_items()

        for item in player_items:
            player_container.delete_item(item, partition_key=item["id"])

        for item in prompt_items:
            prompt_container.delete_item(item, partition_key=item["username"])

    #if the user is in the database, update values correctly
    def test_login_user_exists(self):
        user_login = { "username": "Danny", "password": "mypassword", "add_to_games_played": 5, "add_to_score": 5 }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.player_update(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "OK"
        print(is_failed, json.loads(response.get_body())["msg"])
        self.assertTrue(is_failed and is_logged_in_msg)

        #self.tear_down()
    
    #if the user is not in the database 
    def test_login_user_does_not_exists(self):
        user_login = { "username": "none", "password": "mypassword", "add_to_games_played": 5, "add_to_score": 5 }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.player_update(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Player does not exist"
        self.assertFalse(is_failed and is_logged_in_msg)

        self.tear_down()


if __name__ == '__main__':
    unittest.main()
