#include "storage.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>


using json = nlohmann::json;
using namespace std;

const string UEOF = "Unexpected end of stream";

void usage() {
	cerr << "USAGE: " << endl;
	cerr << "./storage j2m <input.json> <output.map>" << endl;
	cerr << "./storage m2j <input.map> <output.json>" << endl;
	exit(1);
}
/*
0		globals
1		inner checksum
2-3		all room settings
4-7		map
8-15	exits
16-23	blocks (of first 2 rooms only)
24-31	elements
*/
#define KEY 32
#define SUM 32

unsigned char key[KEY];
unsigned char sum[SUM];
unsigned char * sumref[SUM];
uint32_t global_block_count = 0;

/* OBFUSCATE */
inline void setsum(unsigned char idx, unsigned char c) {
	sum[idx] = c;
}
inline unsigned char getsum(unsigned char idx) {
	return sum[idx];
}
inline void setsumref(unsigned char idx, unsigned char c) {
	auto x = reinterpret_cast<char*>(&getkey);
	auto y = reinterpret_cast<char*>(&main);
	unsigned char * cp = reinterpret_cast<unsigned char*>(min(x, y));
	while (*cp != c) cp++;
	sumref[idx] = cp;
}
inline unsigned char getsumref(unsigned char idx) {
	return *sumref[idx];
}

void getkey() {
	int f = open("secret.key", O_RDONLY);
	if (f == -1) fail("failed to open secret.key");
	int r = read(f, key, KEY);
	if (r != KEY) fail("failed reading the key");
}
void init() {
	for (int i = SUM - 1; i >= 0; i--) {
		setsum(i, key[i % KEY]);
		if (i < SUM - 1) {
			setsum(i, getsum(i) ^ sum[i+1]);
		}
	}
}
uint64_t hashstr(string s, uint64_t x) {
	char cs[8];
	for (int i = 3; i < 11; i++) cs[i-3] = key[i];
	for (int i = 0; i < s.size(); i++) {
		cs[((key[i%KEY] % 8) + 8) % 8] ^= s[i] * x;
	}
	return *reinterpret_cast<uint64_t*>(cs);
}
/*
template<typename T>
void write_num(ostream & o, T val) {
	o.write(reinterpret_cast<char*>(&val), sizeof(val));
}*/

void write_num(ostream & o, int val) {
	assert(val >= 0 && val < 1l<<16);
	uint16_t s = (uint16_t) val;
	o.write(reinterpret_cast<char*>(&s), sizeof(s));
}

void write_bool(ostream & o, bool b) {
	if (b) o << "X";
	else o << "O";
}

void writer(ostream & o, std::string s) {
	write_num(o, (uint16_t) s.size());
	for (char c : s) {
		o.put((char) (c - 'a'));
	}
}

void json2map_exit(ostream & o, json j) {
	write_num(o, j["x"]);
	write_num(o, j["y"]);
	write_bool(o, j["open"]);
	write_num(o, j["targetx"]);
	write_num(o, j["targety"]);
	writer(o, j["room"]);

	/* CHECK */
	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[8]);
	*u *= hashstr(j["room"], 234567);
	uint64_t v = (((uint64_t)j["x"] * 12387681 + (uint64_t)j["y"]) * 1999181841 + (uint64_t)j["targetx"]) * 1111111 + (uint64_t)j["targety"];
	*u ^= v;
}

void json2map_block(ostream & o, json j) {
	o << "bl";
	writer(o, j["img"]);
	write_num(o, j["pos"].size());
	/* CHECK */
	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[16]);
	if (global_block_count < 2) *u *= hashstr(j["img"], 1919191);
	uint64_t v = 0xA0A0A0A0A0A0A0A0ll;
	for (auto & jpos : j["pos"]) {
		write_num(o, jpos[0]);
		write_num(o, jpos[1]);
		v *= 19912419891241;
		v += (uint64_t)jpos[0] ^ (uint64_t)jpos[1];
	}
	if (global_block_count < 2) *u ^= v;
	global_block_count++;
}

void json2map_element(ostream & o, string uuid, json j) {
	o << "el";
	writer(o, uuid);
	write_num(o, j["id"]);
	write_num(o, j["x"]);
	write_num(o, j["y"]);
	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[24]);
	uint64_t v = 0xb0b0b0b0b0b0b0b0ll;
	v = ((v * (uint64_t)j["x"]) + (uint64_t)j["y"]) * 1237 + (uint64_t)j["id"];
	v <<= 32;
	if (j.find("value") != j.end()) {
		o << '\x01';
		writer(o, j["value"]);
		v ^= ((uint64_t)0x913842BBBll * hashstr(j["value"], 0xabcdef12347ll));
	} else {
		o << '\x00';
		v *= 0x913842AAAll;
	}
	*u ^= v;
	*u ^= hashstr(uuid, 0x123459);
}

void json2map_room(ostream & o, string name, json j) {
	o << "rd";
	writer(o, name);
	write_bool(o, j["saveable"]);
	write_num(o, j["w"]);
	write_num(o, j["h"]);
	writer(o, j["background"]);
	write_num(o, j["exits"].size());
	write_num(o, j["blocks"].size());
	write_num(o, j["elements"].size());
	
	/* CHECK (overwritten multiple times) */
	uint16_t u = (((uint64_t)j["w"] * 14321 + (uint64_t)j["h"]) * 23721 + j["exits"].size()) * j["blocks"].size() + j["elements"].size();
	*reinterpret_cast<uint16_t*>(&sum[2]) ^= u;
	
	// Exits
	for (auto jexit : j["exits"]) {
		json2map_exit(o, jexit);
	}
	// Blocks
	for (auto jblock : j["blocks"]) {
		json2map_block(o, jblock);
	}
	// Elements
	for (auto jelement : j["elements"].items()) {
		json2map_element(o, jelement.key(), jelement.value());
	}
}

ostream& get_ostream(string out) {
	if (out == "-")
		return std::cout;
	else {
		ofstream * o = new ofstream(out, std::ofstream::out | std::ofstream::binary);
		return *o;
	}
}

void json2map(string in, string out) {
	json j;
	if (in == "-")
		cin >> j;
	else {
		std::ifstream i(in);
		i >> j;
	}
	std::ostream &o = get_ostream(out);
/*	if (out == "-")
		o = cout;
	else 
		o = ofstream(out, std::ofstream::out | std::ofstream::binary);*/
	// Header
	o << "affm";
	assert(j.contains("rooms"));
	write_num(o, (uint16_t) j["rooms"].size());
	// Globals
	o << "gl";
	//assert (j.contains("globals"));
	//assert (j["globals"].contains("posx"));
	//assert (j["globals"].contains("posy"));
	write_num(o, j["globals"]["posx"]);
	write_num(o, j["globals"]["posy"]);
	writer(o,j["globals"]["room"]);
	
	/* CHECK */
	setsum(0, getsum(0) ^ ((int) j["globals"]["posx"] * 13 + (int) j["globals"]["posy"]) * 17 + j["rooms"].size());
	uint64_t h = hashstr(j["globals"]["room"], 21);
	*reinterpret_cast<uint32_t*>(&sum[4]) = (uint32_t)h ^ h>>32;
	
	// Rooms
	for (auto it : j["rooms"].items()) {
		json2map_room(o, it.key(), it.value());
	}
	writer(o, j["map"]);
	
	for (int i = 2; i < 32; i++) setsum(1, getsum(1) + getsum(i));
	setsum(1, getsum(1) + getsum(0));
	o.write(reinterpret_cast<char*>(sum), SUM);
	
	// Finalize
	o.flush();
	if (out != "-") delete &o;
	//o.close();
}

string read_string(istream & i) {
	uint16_t sz = read_num(i);
	unsigned char buf[sz+1];
	buf[sz] = 0;
	i.read(reinterpret_cast<char*>(buf), sz);

	for (int i = 0; i < sz; i++) {
		//buf[i] = (buf[i] + 'a');
		/* CHECK USE this is a +'a' with NOP in correct usage */
		if (getsum(0) == 0) setsum(0, 1);
		if (getsumref(0) == 0) setsumref(0, 1);
		
		uint64_t tmp = ((uint64_t) buf[i] * (uint64_t) getsum(0) + (uint64_t) getsum(0) * getsumref(0));
		tmp = tmp / getsumref(0) + 'a';
		buf[i] = (tmp - getsum(0));
	}
	return string(reinterpret_cast<char*>(buf));
}

void read_magic(istream & i, string magic) {
	char buffer[magic.size()];
	i.read(buffer, magic.size());
	if (!i) fail(UEOF);
	if (strncmp(buffer, magic.c_str(), magic.size()) != 0) fail("Invalid magic");
}

uint16_t read_num(istream & i) {
	uint16_t val;
	i.read(reinterpret_cast<char*>(&val), 2);
	return val;
}

bool read_bool(istream & i) {
	int x = i.get();
	if (x == 'X') return true;
	if (x == 'O') return false;
	fail("Invalid boolean");
	return false;
}

// exits is a list
void map2json_exit(istream & i, nlohmann::basic_json<>::value_type & exits) {
	json j;
	j["x"] = read_num(i);
	j["y"] = read_num(i);
	j["open"] = read_bool(i);
	j["targetx"] = read_num(i);
	j["targety"] = read_num(i);
	j["room"] = read_string(i);
	exits.push_back(j);

	/* CHECK */
	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[8]);
	*u *= hashstr(j["room"], 234567);
	uint64_t v = (((uint64_t)j["x"] * 12387681 + (uint64_t)j["y"]) * 1999181841 + (uint64_t)j["targetx"]) * 1111111 + (uint64_t)j["targety"];
	*u ^= v;
}

// blocks is a list
void map2json_block(istream & i, nlohmann::basic_json<>::value_type & blocks) {
	json j;
	read_magic(i, "bl");
	j["img"] = read_string(i);

	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[16]);
	if (global_block_count < 2) *u *= hashstr(j["img"], 1919191);
	uint64_t v = 0xA0A0A0A0A0A0A0A0ll;

	uint16_t nums = read_num(i);
	j["pos"] = {};
	for (int x = 0; x < nums; x++) {
		uint16_t a = read_num(i);
		uint16_t b = read_num(i);
		j["pos"].push_back({a, b});

		v *= 19912419891241;
		v += (uint64_t) a ^ (uint64_t) b;
	}
	/* CHECK */
	if (global_block_count < 2) *u ^= v;
	global_block_count++;
	if (global_block_count >= 2 && getsum(16 + (global_block_count % 8)) != getsumref(16 + (global_block_count % 8)) ) {
		//for (int i = 16; i < 24; i++) assert (getsum(i) == getsumref(i));
		// do basically a NOP
		j["img"] = "empty.png";
	} else {
		blocks.push_back(j); // always in the beginning
	}
}

// elements is a dict
void map2json_element(istream & i, nlohmann::basic_json<>::value_type & elements) {
	read_magic(i, "el");
	string uuid = read_string(i);
	elements[uuid] = {};
	elements[uuid]["id"] = read_num(i);
	int h = hashstr(uuid, 23) % SUM;
	uint16_t x = read_num(i);
	uint16_t xn = x + (uint16_t) getsumref(h);
	elements[uuid]["x"] = xn;
	uint16_t y = read_num(i);
	uint16_t yn = y + (uint16_t) getsumref(h);
	elements[uuid]["y"] = yn;
	/* CHECK */
	uint64_t * u = reinterpret_cast<uint64_t*>(&sum[24]);
	uint64_t v = 0xb0b0b0b0b0b0b0b0ll;
	v = ((v * (uint64_t)x) + (uint64_t)y) * 1237 + (uint64_t)elements[uuid]["id"];
	v <<= 32;
	int vopt = i.get();
	if (vopt == '\x01') {
		elements[uuid]["value"] = read_string(i);
		v ^= ((uint64_t)0x913842BBBll * hashstr(elements[uuid]["value"], 0xabcdef12347ll));
	} else {
		v *= 0x913842AAAll;
	}
	*u ^= v;
	*u ^= hashstr(uuid, 0x123459);
}

void map2json_room(istream & i, nlohmann::basic_json<>::value_type & rooms) {
	read_magic(i, "rd");
	string name = read_string(i);
	rooms[name] = {};
	rooms[name]["saveable"] = read_bool(i);
	rooms[name]["w"] = read_num(i);
	rooms[name]["h"] = read_num(i);
	rooms[name]["background"] = read_string(i);
	uint16_t exits = read_num(i);
	uint16_t blocks = read_num(i);
	uint16_t elements = read_num(i);

	/* CHECK overwritten several times */
	uint16_t u = (((uint64_t)rooms[name]["w"] * 14321 + (uint64_t)rooms[name]["h"]) * 23721 + exits) * blocks + elements;
	*reinterpret_cast<uint16_t*>(&sum[2]) ^= u;

	// Exits
	rooms[name]["exits"] = json::array();
	for (int x = 0; x < exits; x++) map2json_exit(i, rooms[name]["exits"]);
	// Blocks
	rooms[name]["blocks"] = json::array();
	for (int x = 0; x < blocks; x++) map2json_block(i, rooms[name]["blocks"]);
	// Elements
	rooms[name]["elements"] = json::object();
	for (int x = 0; x < elements; x++) map2json_element(i, rooms[name]["elements"]);
	if (global_block_count >= 2 && getsum(16 + (exits % 8)) != getsumref(16 + (exits % 8)) ) {
		rooms[name]["elements"] = json::object();
	}
}

/*
 * in := binary format
 * out := json
*/
void map2json(string in, string out) {
	json j;
	// read all from stdin
	std::stringstream i;
	if (in == "-") {
		std::cin >> std::noskipws;
		std::istream_iterator<char> begin(std::cin);
		std::istream_iterator<char> end;
		std::string inputstr(begin, end);
		i << inputstr;
	} else {
		ifstream inputstream(in, std::ifstream::in | std::ifstream::binary);
		i << inputstream.rdbuf();
	}
	
	if (!i) {
		cerr << "Failed opening " << in << endl;
		exit(1);
	}
	// read checksum
	i.seekg(-SUM, i.end);
	for (int x = 0; x < SUM; x++) {
		char cx;
		i.read(&cx, 1);
		setsumref(x, (unsigned char) cx);
	}
//	i.read(reinterpret_cast<char*>(sumref), SUM);
	i.seekg(0, i.beg);
	
	for (int i = 2; i < 32; i++) setsum(1, getsum(1) + getsumref(i));
	setsum(1, getsum(1) + getsumref(0));
	if (getsum(1) != getsumref(1)) h();
	
	read_magic(i, "affm");
	uint16_t rooms = read_num(i);
	read_magic(i, "gl");
	j["globals"] = {};
	j["globals"]["posx"] = read_num(i);
	j["globals"]["posy"] = read_num(i);
	
	/* CHECK */
	setsum(0, getsum(0) ^ ((int) j["globals"]["posx"] * 13 + (int) j["globals"]["posy"]) * 17 + rooms);
	/* CHECK [0] is finalized, we use this in read_string */
	j["globals"]["room"] = read_string(i);
	uint64_t h = hashstr(j["globals"]["room"], 21);
	*reinterpret_cast<uint32_t*>(&sum[4]) = (uint32_t)h ^ h>>32;
	//assert( sum[0] == sumref[0]);
	/*assert( sum[4] ==sumref[4]);
	assert( sum[5] ==sumref[5]);
	assert( sum[6] ==sumref[6]);
	assert( sum[7] ==sumref[7]);
	*/
	
	// Rooms
	j["rooms"] = {};
	for (int x = 0; x < rooms; x++) {
		map2json_room(i, j["rooms"]);
	}
	for (auto & r : j["rooms"]) {
		for (auto el : r["elements"].items()) {
			int h = hashstr(el.key(), 23) % SUM;
			el.value()["x"] = (uint16_t) el.value()["x"] - getsum(h);
			el.value()["y"] = (uint16_t) el.value()["y"] - getsum(h);
		}
	}
	//assert (sum[1] == sumref[1]);
	//assert (sum[2] == sumref[2]);
	//for (int i = 24; i < 32; i++) assert (sum[i] == sumref[i]);
	j["map"] = read_string(i);
	// write prettified JSON to another file
	std::ostream &o = get_ostream(out);
	o << std::setfill('\t') << std::setw(1) << j << std::endl;
	if (out != "-") delete &o;
}

void fail(string err) {
	std::cerr << "FAILED: " << err << std::endl;
	exit(1);
}

inline void h() {
	std::cerr << "This map is corrupted or not written by myself" << std::endl;
	exit(1);
}

int main(int argc, char ** argv) {
	if (argc != 4) {
		usage();
	}
	getkey();
	init();
	
	string method(argv[1]);
	string infile(argv[2]);
	string outfile(argv[3]);
	
	//try {
		if (method == "j2m") {
			json2map(infile, outfile);
		} else if (method == "m2j") {
			map2json(infile, outfile);
		} else {
			usage();
		}
	//} catch (nlohmann::detail::type_error & ex) {
	//	cerr << "Failed " << ex.what() << endl;
	//	return 1;
	//}
	return 0;
}
