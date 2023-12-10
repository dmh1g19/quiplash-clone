import unittest
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
from prompt_create import PromptCreate

#Asumming the database already contains an entry s.t: { "username": "Danny", "password": "mypassword" }

class test_create(unittest.TestCase):
    create_instance = PromptCreate(
       endpoint = "https://quiplashy.documents.azure.com:443/",
       key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw==",
       database_name = "quiplash",
       player = "player",
       key_translater =  "c17da301f1534fb78e4bc79cbcb3ece4",
       endpoint_translater = "https://api.cognitive.microsofttranslator.com/",
       location = "uksouth",
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

    #The players exists in the databse and has a prompt container as well
    def test_prompt_create_success(self):
        user_login = { "text": "Hello, how is every doing?", "username": "Danny" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_create(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "OK"
        self.assertTrue(is_failed and is_logged_in_msg)

        #self.tear_down()

    #If the player doesnt exist        
    def test_prompt_create_player_doesnt_exist(self):
        user_login = { "text": "Hello, how is every doing?", "username": "none" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_create(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Player does not exist"
        self.assertFalse(is_failed and is_logged_in_msg)

        #self.tear_down()
    
    #If the prompt text is < 15
    def test_prompt_create_less_than_15(self):
        user_login = { "text": "", "username": "none" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_create(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Prompt less than 15 characters or more than 80 characters"
        self.assertFalse(is_failed and is_logged_in_msg)

    #    #self.tear_down()
    
    #If the prompt text is < 80
    def test_prompt_create_grater_than_80(self):
        user_login = { "text": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "username": "none" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_create(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Prompt less than 15 characters or more than 80 characters"
        self.assertFalse(is_failed and is_logged_in_msg)

    #    #self.tear_down()
    
    #If the language provided is unsupported
    def test_prompt_create_language_not_supported(self):
        user_login = { "text": "123111111111111232323232323232323232323", "username": "Danny" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_create(request)

        is_failed = json.loads(response.get_body())["result"]
        is_logged_in_msg = json.loads(response.get_body())["msg"] == "Unsupported language"
        print("TEST", is_failed, json.loads(response.get_body())["msg"])
        self.assertFalse(is_failed and is_logged_in_msg)

        self.tear_down()
    

if __name__ == '__main__':
    unittest.main()
