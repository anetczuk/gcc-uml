///

#include <time.h>       // time


int calc_valC(const int valueC) {
	int arrY[5];
	int arrX[2] = {10, 20};
	arrX[0] += valueC;
	arrX[1] = valueC / 2.1;
	const int xxxB = arrX[1] * 3 + arrX[0];
	return xxxB;
}


const long calc_valB(const int valueB) {
	int timestamp = time(nullptr);
	timestamp = timestamp + 1;
	timestamp += timestamp + 2;
	const int bbb = timestamp + 11;
	if ( bbb % 2 == 0 ) {
		const int ccc = 0;
		return ccc;
	} else {
		const int ddd = 4 * valueB;
		return ddd;
	}
}


int calc_valA(const int valueA) {
	int xxxA = valueA * 2.1 + 3;
	const int xxxB = xxxA * 3;
	return xxxB;
}


int main() {
	const int aaa = calc_valA(4);
	int bbb = calc_valB(aaa);
	return calc_valC(bbb);
}
