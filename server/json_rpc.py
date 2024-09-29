
from json import loads

class JsonRpc:
    def __init__(self):
        self.mCommands = {
            "Command1" : self._command1,
        }

    def process_json(self, json_str):
        json_obj = loads(json_str)
        command = json_obj["method"]
        params = json_obj["params"]
        self._call_command(command, params)

    def _call_command(self, command, params):
        self.mCommands[command](params)

    def _command1(self, params):
        print("hello")
        print(params)


if __name__ == '__main__':
    json = JsonRpc()
    json.process_json("{\"method\": \"Command1\", \"params\": {}}")
