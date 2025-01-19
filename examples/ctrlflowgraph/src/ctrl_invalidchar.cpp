///

#include <cstdint>

int main() {
	const char *bad_char = "\xff";
	uint8_t bad_char_array[3] = { 255, 65, 255 };
	return 0;
}
