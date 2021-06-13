The Lost Bottle
================


This service is a small client-server-game. The challange is about reversing a custom file format.

Usage
================
Im Verzeichnis `src`:

Starte den server-teil
```
make run-server
```

Starte den Spielclient
```
make run-client
```
Exploits in exploit/ (there are currently 3 different exploits)
```
python exploit.py <server> <port> <mapname> <exploitmap>
mapname: Name of Map on the server (maps/somename.json)
exploitmap: the modified save state is written here for debugging reasons
```

Das Makefile lässt auch erkennen, wie andere Optionen gestartet werden.

Als Service hat jeder den Client zur Verfügung um zum Spielen.


Commands
=================
- Arrow-Keys : move
- S : create a save game in the current folder
- Q : end the game
- E : interact with an element in range or travel with a ship

Challange - contains Spoilers
=================
The Game:
- The game is a 3rd person 3D game where you can explore different rooms.
- The server has a list of maps that can be played (this list ist populated by the service checker)
- Each map contains a flag e.g. written on an in-game sign, but normally the corresponding room is not accessible with normal in-game actions.

Possible Interactions with the server:
- Start playing on a new map
- Download the current game state as a save game
  - contains most parts of the map, but misses 'restricted' information (the flag, bottle values)
  - uses a custom binary format
- Upload a save game to continue playing
  - uses a simple json format

Exploits:
==================
All exploits need the previous reversing/understanding of the binary format
Probably the best way is to download several slightly different maps and investigate the changes first. The binary format is not very difficult, but contains some unusal gimmicks to make this challange interesting.
The flag is always stored in two positions in the map: Written on one sign, and a dream.

## Secret Room Exploit
1. Parse the Map state, find the location of the flag sign
2. Construct a compatible save game, that allows entering the secret room with the sign (medium; understand the map loading python code).
  - e.g. the door connections are not checked to be bijective. Add a new additional room with an exit to the secret room
  - or change the exit of the current room (not tested)
3. Upload the custom save game and play to it's end (easy; API usage)
#### Fix
Check uploading consistency or forbid changing map layout completely.

## Bottle Exploit
1. Find a bottle and change its value to "4|100%" (savegame does not contain bottle values, but adding the value reads it in parsing mode
2. Upload the map and drink this bottle
#### Fix
Do not allow to modify the bottle value

## Type Change Exploit
1. Change the type of all bottles to barrels
2. Upload the map and interact with all bottles/barrels. This now prints the bottle value
3. Sort the bottles by percentage (ascending)
4. Play the original map again and drink the bottles in ascending order for maximum alcohol level at the end
Note 1: Guessing the correct drinking order without any exploits is theoretically possible. Yet, chances seem to be far below 1:20000000.
Note 2: The sign type can be changed as well, but this does not help because you need to enter the secret room to access it.

#### Fix
Do not allow type changes


Binformat Fun
==================
The binformat binary (compiled from storage.cpp) is intended to not be analyzed during the competition (or be more complicated than blackbox testing). A few fun things are implemented:
- Checksum: The characters of strings are modified using a function `f(realchar, checksum, checksumexpected)` that behaves like a NOP instruction when the checksum equals the expected one. Otherwise it produces garbage. This is done using a checksum byte, that is computed really early in the process.
- Checksum: Positions of elements are shifted by a checksumexpected value during decoding and only get unshifted using the computed checksum at the end.
- Checksum: If the checksum does not match, elements of the map are simply dropped
- the reference check sum is stored indirectly: Instead of storing a byte, a pointer to an code instruction with this value is stored. Therefore, the reference checksum is never directly stored in memory.
