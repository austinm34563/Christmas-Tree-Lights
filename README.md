# Christmas-Tree-Lights

This is a general purpose Christmas tree lighting project. There
are a variety of functionalites:
1. Set RGB values for all lights.
2. Set color palettes to lights.
3. Run a variety of effects.
4. Play and sync music to lights.

There are two main components of the software:
1. Server:
    - server that runs on the Rasberry Pi
    - all calls are executed through JSON-RPC
    - clients communicate to the server via TCP
    - clients can send a variety of RPC api calls
    - all calls to the server should be non-blocking
2. CLI Client:
    - example client used to demo lighting protocol
    - client establishes a connection over TCP

## Hardware
### Microcontroller
- Rasberry Pi 4

### Light Strips
- Neopixel (WS2811)

## JSON-RPC APIs

### Requests
In general, there are two main components when sending json data:
***method*** name and ***params***. The ***params*** tag will hold a variety
of tags that are associated with the method.
```shell
{"method": "foo", "params": {"param1": 11, "param2": "Hello, World!"}}
```

### Response
Reponses can be in two forms: ***Results*** (only can be sent on success)
and ***Errors*** (only can be sent on failure).


#### Results
Results occur when a request was successful. Typically the associated
result tag is the corresponding return data to the request.

Example 1 (basic bool):
```shell
{"result": true}
```

Example 2 (list of data):
```shell
{"result": [1, 2, 4, 5]}
```

Example 3 (nest json):
```shell
{"result": {"result_tag1": 15, "result_tag2": "Hello, World!"}}
```

#### Errors
Errors occur when a request was **NOT** successful. Typically the associated
error tag/key will point to a "code" and "message" explaining the type of error.

Example:
```shell
{
    "error": {
        "code": -32602,
        "message": "Invalid params"
    }
}
```

Below are the list of error codes and their corresponding message:

    - PARSE_ERROR (-32700): "Parse error"
    - INVALID_REQUEST (-32600): "Invalid Request"
    - METHOD_NOT_FOUND (-32601): "Method not found"
    - INVALID_PARAMS (-32602): "Invalid params"
    - MUSIC_NOT_PLAYING_ERROR (-32000): "No music is currently playing"

### Set Color
Below sets the color to red (0xFF0000).
```shell
{"method": "set_light", "params": {"color": "0xff0000"}}
```

Below sets the color to beige (0xF5F5DC)
```shell
{"method": "set_light", "params": {"color": "0xf5f5dc"}}
```

### Set Color Palette
A color palette can be applied to the lights. This can be a custom
palette, or a palette that is pre-defined from the server. (Note: the
color values in the palette are sent as integers in base 10. This
currently conflicts with setting a single color to the tree, as that
sends the value as a hex string. This will be aligned in the future).

Example:
```shell
{"method": "set_pallete", "params": {"pallete": [1997856, 11927552, 14331, 14640384, 8454363]}}
```

### Get Color Palette
The light server holds a variety of color palettes. The client can
request the list of palettes.

Send:
```shell
{"method": "get_palettes", "params": {}}
````

Potential Response:
```shell
{
    "result": {
        "Christmas Tree Palette": [1997856, 11927552, 14331, 14640384, 8454363],
        "Christmas Snow": [14353412, 1482568, 9229567, 13037567, 16777215],
        "Generic Christmas": [16711680, 16742520, 16777215, 7657088, 3640105],
        "Christmas Palette Traditional": [1997856, 11927552, 16777215, 14640384, 65280],
        "Christmas Palette Winter": [10995687, 16777215, 11119017, 4103837, 16711680],
        "Christmas Palette Cozy": [9127187, 16766720, 10824234, 25600, 16777215],
        "Christmas Palette Classic": [25600, 11927552, 16766720, 16777215, 17663],
        "Christmas Palette Elegant": [6970061, 16777215, 16766720, 16711935, 11674146, 2263842],
        "Christmas Palette Elegant II": [6970061, 16777215, 16711935, 11674146, 2263842],
        "Candle Colors": [16737300, 16732160, 13127680, 13114880, 16714240]
    }
 }
```

### Set Effect
TBD

### Get Effect List
TBD

### Start Music Sync
TBD

### Stop Music Sync
TBD

### Get List of Songs
TBD
