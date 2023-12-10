import unittest
from azure.cosmos import exceptions, CosmosClient
import azure.functions as func
import json
from prompt_delete import PromptDelete

#Asumming the database already contains an entry s.t: { "username": "Danny", "password": "mypassword" }

class test_prompt_delete(unittest.TestCase):
    create_instance = PromptDelete(
       endpoint = "https://quiplashy.documents.azure.com:443/",
       key = "aBD5f8vSUTcyVtpcsPrwRXfu5GmVUWB76w8XAtffLZaAexp6DnRVRUnKpgpXeVjZg7RmByYcdHKyACDblRgECw==",
       database_name = "quiplash",
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

    #The players exists in the database and has a prompt container as well, delete all prompts
    def test_prompt_create_success(self):
        user_login = { "player": "Danny" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_delete(request)

        is_failed = json.loads(response.get_body())["result"]
        self.assertTrue(is_failed)

        #self.tear_down()
    
    #The players exists in the database and has a prompt container as well, delete prompts with words
    def test_prompt_create_success(self):
        user_login = { "word": "Hello" }
        request = func.HttpRequest(
            method='POST',
            body=json.dumps(user_login).encode('utf-8'),
            url='/https://quiplashy.documents.azure.com:443/'
        )
        response = self.create_instance.prompt_delete(request)

        is_failed = json.loads(response.get_body())["result"]
        self.assertTrue(is_failed)

        self.tear_down()
    

if __name__ == '__main__':
    unittest.main()
