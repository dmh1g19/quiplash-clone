import unittest
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
from player_register import PlayerRegistration

class test_register(unittest.TestCase):
    registration_instance = PlayerRegistration(
       endpoint = "https://quiplashy.documents.azure.com:443/",
       key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw==",
       database_name = "quiplash",
       player = "player",
       prompt = "prompt"
    )

    #Empty both containers
    def tear_down(self):
        client = self.registration_instance.getClient()

        player_container = client.get_database_client("quiplash").get_container_client("player")
        prompt_container = client.get_database_client("quiplash").get_container_client("prompt")

        player_items = player_container.read_all_items()
        prompt_items = prompt_container.read_all_items()

        for item in player_items:
            player_container.delete_item(item, partition_key=item["id"])

        for item in prompt_items:
            prompt_container.delete_item(item, partition_key=item["username"])

    #Already registered users handled correctly
    def test_already_registered(self):
        player_item = {
            "id": "100",
            "username": "danny",
            "password": "password123",
            "games_played": 0,
            "total_score": 0
        }
        player_client = self.registration_instance.getClient()
        container = player_client.get_database_client("quiplash").get_container_client("player")
        container.create_item(player_item)

        user_registered = { "username": "danny", "password": "password123" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_registered).encode('utf-8'), #converts the JSON string to bytes with UTF-8 encoding before setting it as the request body
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.registration_instance.player_register(request)

        is_failed = json.loads(response.get_body())["result"]
        is_registered_msg = json.loads(response.get_body())["msg"] == "Username already exists"
        self.assertFalse(is_failed and is_registered_msg)

        self.tear_down()

    #Handles new users correctly
    def test_not_registered(self):
        user_registered = { "username": "danny", "password": "mypassword123" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_registered).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.registration_instance.player_register(request)

        is_failed = json.loads(response.get_body())["result"]
        is_registered = json.loads(response.get_body())["msg"] == "OK"
        self.assertTrue(is_failed and is_registered)

        self.tear_down()

    #If the username is too short
    def test_username_length(self):
        user_registered = { "username": "dny", "password": "password123" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_registered).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.registration_instance.player_register(request)

        is_failed = json.loads(response.get_body())["result"]
        is_registered_msg = json.loads(response.get_body())["msg"] == "Username less than 4 characters or more than 14 characters"
        self.assertFalse(is_failed and is_registered_msg)

        self.tear_down()
    
    #If the password is too short
    def test_password_length(self):
        user_registered = { "username": "danny", "password": "pass" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_registered).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.registration_instance.player_register(request)

        is_failed = json.loads(response.get_body())["result"]
        is_registered_msg = json.loads(response.get_body())["msg"] == "Password less than 10 characters or more than 20 characters"
        self.assertFalse(is_failed and is_registered_msg)

        self.tear_down()


if __name__ == '__main__':
    unittest.main()
