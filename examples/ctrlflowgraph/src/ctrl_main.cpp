///

#include <time.h>       // time


const long calc_valB(const int value) {
	int timestamp = time(nullptr);
	timestamp = timestamp + 1;
	timestamp += timestamp + 2;
	const int bbb = timestamp + 11;
	if ( bbb % 2 == 0 ) {
		const int ccc = 0;
		return ccc;
	} else {
		const int ddd = 4 * value;
		return ddd;
	}
}


int calc_valA(const int value) {
	int xxxA = value * 2.1 + 3;
	const int xxxB = xxxA * 3;
	return xxxB;
}


int main() {
	const int aaa = calc_valA(4);
	return calc_valB(aaa);
}
