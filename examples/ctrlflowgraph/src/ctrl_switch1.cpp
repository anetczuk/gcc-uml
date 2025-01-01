///

#include <time.h>       // time


int calc_switch4() {
	int timestamp = time(nullptr);
	switch(timestamp % 3) {
	case 0: return 0;
	case 1: return 1;
	case 2: return 2;
	default: {
		timestamp = time(nullptr);
	}
	}
	timestamp *= 3;
	return timestamp % 2;
}


int calc_switch3() {
	int timestamp = time(nullptr);
	switch(timestamp % 3) {
	default: timestamp = time(nullptr);
	}
	return -3;
}


int calc_switch2() {
	const int timestamp = time(nullptr);
	switch(timestamp % 3) {
	default: return 0;
	}
	return -3;
}


int calc_switch1() {
	const int timestamp = time(nullptr);
	switch(timestamp % 3) {
	case 0: return 0;
	}
	return -3;
}
