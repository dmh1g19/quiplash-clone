import unittest
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
from player_login import PlayerLoggin 

#Asumming the database already contains an entry s.t: { "username": "Danny", "password": "mypassword" }

class test_login(unittest.TestCase):
    login_instance = PlayerLoggin(
       endpoint = "https://quiplashy.documents.azure.com:443/",
       key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw==",
       database_name = "quiplash",
       player = "player",
       prompt = "prompt"
    )

    #Empty both containers
    def tear_down(self):
        client = self.login_instance.getClient()

        player_container = client.get_database_client("quiplash").get_container_client("player")
        prompt_container = client.get_database_client("quiplash").get_container_client("prompt")

        player_items = player_container.read_all_items()
        prompt_items = prompt_container.read_all_items()

        for item in player_items:
            player_container.delete_item(item, partition_key=item["id"])

        for item in prompt_items:
            prompt_container.delete_item(item, partition_key=item["username"])

    #if the user is in the database 
    def test_login_user_exists(self):
        user_login = { "username": "Danny", "password": "mypassword" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.login_instance.player_login(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "OK"
        print(is_failed, json.loads(response.get_body())["msg"])
        self.assertTrue(is_failed and is_logged_in_msg)

        #self.tear_down()

    #if the username is incorrect 
    def test_login_user_wrong_username(self):
        user_login = { "username": "notreal", "password": "mypassword" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.login_instance.player_login(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Username or password incorrect"
        self.assertFalse(is_failed and is_logged_in_msg)

        #self.tear_down()
    
    #if the password is incorrect 
    def test_login_user_wrong_username(self):
        user_login = { "username": "Danny", "password": "none" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.login_instance.player_login(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Username or password incorrect"
        self.assertFalse(is_failed and is_logged_in_msg)

        self.tear_down()


if __name__ == '__main__':
    unittest.main()
