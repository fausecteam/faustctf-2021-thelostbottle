import json
import base64
import sys
from struct import *

RECV_SIZE = 512
MAX_MSG_SIZE = 2**20

"""
socket := socket to sent to
msg: message as a json object
"""
def send_json(socket, msg):
	msg_str = json.dumps(msg).encode()
	msg_encoded = base64.b64encode(msg_str)
	mlen = len(msg_encoded)
	assert mlen <= MAX_MSG_SIZE, "Message too long"
	sz = pack('I', mlen)
	socket.send(sz)
	socket.send(msg_encoded)
	socket.send(sz)

"""
receive exactly n bytes
"""
recv_buffer = b''
def recv_bytes(socket, n):
	global recv_buffer
	while len(recv_buffer) < n:
		r = socket.recv(RECV_SIZE)
		if r == b'':
			raise ConnectionResetError("Disconnect")
		recv_buffer += r
	ret = recv_buffer[:n]
	recv_buffer = recv_buffer[n:]
	return ret

"""
receive a json object
"""
def recv_json(socket):
	sz = recv_bytes(socket, 4)
	mlen = unpack('I', sz)[0]
	assert mlen <= MAX_MSG_SIZE, "Message size too large {}".format(mlen)
	msg_encoded = recv_bytes(socket, mlen)
	sz2 = recv_bytes(socket, 4)
	mlen2 = unpack('I', sz2)[0]
	assert mlen2 == mlen, "Sizes do not match"
	msg_str = base64.b64decode(msg_encoded)
	msg = json.loads(msg_str)
	return msg

"""
pair of sending a message and receiving an answer
"""
def communicate(socket, msg):
	send_json(socket, msg)
	m = recv_json(socket)
	if not m["success"]:
		print(m["msg"])
		sys.exit(1)
	return m["msg"]

""" Check if dictionary 'j' has every key in 'parts' """
def check_has(j, parts):
	if not isinstance(j, dict):
		raise RuntimeError("Error")
	for p in parts:
		if p not in j:
			raise RuntimeError(f"Missing {p} in {j}")

def fail(msg):
	raise Exception("Failed " + msg)
