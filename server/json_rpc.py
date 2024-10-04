
from json import loads
from logger import Logger

METHOD_TAG = "method"
PARAMS_TAG = "params"

VALID_TAGS = [METHOD_TAG, PARAMS_TAG]

logger = Logger()

TAG = "JsonRpc"

class JsonRpc:
    def __init__(self):
        # todo add more commands
        self.mCommands = {
            "set_light" : self._set_light,
            "trigger_effect" : self._trigger_effect,
        }

    def process_json(self, json_str):
        try:
            json_obj = loads(json_str)

            if not self._validate_json(json_obj):
                return False

            self._call_command(json_obj[METHOD_TAG], json_obj[PARAMS_TAG])
            return True
        except:
            logger.error(TAG, "Error: Could not read json")
            return False

    def _validate_json(self, json_obj):
        if not isinstance(json_obj, dict):
            logger.error(TAG, "Error: Invalid JSON dictionary.")
            return False

        for tag in VALID_TAGS:
            if json_obj.get(tag) is None:
                logger.error(TAG, "Error: Invalid JSON. Missing the following tag: ", tag)
                return False

        return True

    def _call_command(self, command, params):
        if self.mCommands.get(command) is None:
            logger.error(TAG, "Error: JSON-RPC command not found")
            return False

        self.mCommands[command](params)
        return True

    def _set_light(self, params):
        logger.info("Calling set light")
        # todo - make calls to lighting

    def _trigger_effect(self, params):
        logger.info("Triggering some effect")
        # todo - make calls to effects
