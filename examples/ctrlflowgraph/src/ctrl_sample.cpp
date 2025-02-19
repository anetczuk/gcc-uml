///

#include <time.h>       // time

class ExampleClass {
public:
	int switchExample(const int paramA) {
		int timestamp = time(nullptr);
		if ( timestamp % 2 == 0 ) {
			timestamp += paramA;
		}
		switch(timestamp % 3) {
		case 0:
			if (timestamp) {
				return 0;
			} else {
				return 1;
			}
		case 1:
		case 2: return 2;
		default: {
			timestamp = time(nullptr);
		}
		}
		timestamp *= 3;
		if ( timestamp % 2 == 0 ) {
			timestamp += 1;
		} else {
			timestamp += 2;
		}
		return timestamp % 2;
	}
};

int main() {
	ExampleClass obj1;
	return obj1.switchExample(3);
}
