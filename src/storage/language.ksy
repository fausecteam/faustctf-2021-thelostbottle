meta:
  id: language
  endian: le
seq:
  - id: header
    type: header
  - id: globals
    type: globals
  - id: rooms
    type: room
    repeat: "expr"
    repeat-expr: header.nrooms
types:
  header:
    seq:
      - id: magic
        contents: "affm"
      - id: nrooms
        type: u2
  globals:
    seq:
      - id: magic
        contents: "gl"
      - id: x
        type: u2
      - id: y
        type: u2
      - id: currentroomid
        type: string
  string:
    seq:
      - id: sz
        type: u2
      - id: str
        size: sz
        type: str
        encoding: 'ascii'
  room:
    seq:
      - id: magic
        contents: "rd"
      - id: name
        type: string
      - id: width
        type: u2
      - id: height
        type: u2
      - id: background
        type: string
      - id: nexits
        type: u2
      - id: nblocks
        type: u2
      - id: nelements
        type: u2
      - id: exits
        type: exit
        repeat: "expr"
        repeat-expr: nexits
      - id: blocks
        type: block
        repeat: "expr"
        repeat-expr: nblocks
      - id: elements
        type: element
        repeat: "expr"
        repeat-expr: nelements
        
  exit:
    seq:
      - id: x
        type: u2
      - id: y
        type: u2
      - id: target
        type: string
  block:
    seq:
      - id: magic
        contents: "bl"
      - id: texture
        type: string
      - id: npos
        type: u2
      - id: positions
        type: pos
        repeat: "expr"
        repeat-expr: npos
  element:
    seq:
      - id: magic
        contents: "el"
      - id: id
        type: u2
      - id: x
        type: u2
      - id: y
        type: u2
      - id: hasvalue
        type: u1
      - id: value
        type: string
        if: hasvalue == 0x31
  pos:
    seq:
      - id: x
        type: u2
      - id: y
        type: u2
