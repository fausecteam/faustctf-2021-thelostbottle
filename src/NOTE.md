## The Lost Bottle
*The Lost Bottle* is the most awesome pirate game.
It is about a young pirate, that lost her favorite bottle of old rum.
She is now doomed to drink ordinary rum until she finds her bottle.

To play, simply run
`python3 -m client <command> <mapname> [ip]`
Where `<command>` is either `new` (to start a new game) or `load` (to upload and start a saved game). `<mapname>` is either the map filename you want to play (references file on the server, include the `maps/`), or a local save state file that will be uploaded.

#### Requirements
Can run in a VM (maybe access to a real graphics card is required), Docker probably needs some Xauth tweaking to connect to a running X server bypassing the security advantages.
- `python3-dev`
- `python3-pip`
- `libjpeg-dev`
- `zlib1g-dev`
- `pip` package `arcade`
- probably some graphics drivers / OpenGL stuff. (`libx11-dev`, `freeglut3-dev`)

#### Most Remarkable Features
- Awesome 2D game with high end graphics and a sophisticated physics engine
- Continuous Challenges: Frequent updates with new randomized maps
- Interesting storyline
- Large 2D world to explore
- Flexibility: Allows different play styles
- Immediate, useful rewards: Unlocking new areas (we plan to add unlocking new characters)
- Combining Fun and Realism: If you die, you die. If you drink too much, you hallucinate.
- Save and load current game state (we now use a more compact format for saving to reduce bandwidth)
- Easy to use, no install required (except maybe some packages, see below)

#### Changelog
- Initial game
- Improvements (added this changelog, because the game is already perfect)

#### Troubleshooting
- If you have a problem, you probably did something wrong.
- Stop shooting the poor troubles. They did nothing wrong.

#### License
- If you use the images, you owe me $10 per pixel
- If you use the letters from the code (even if you alter the ordering), you owe me money depending on the character usage. E.g. using an `a` is as cheap as $1 for a single use or $10 for up to 20 usese.
- With reading this notice, you agree to the conditions above

