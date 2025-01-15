///

#include <time.h>       // time

class ExampleClass {
public:
	int switchExample(const int paramA) {
		int timestamp = time(nullptr);
		timestamp += paramA;
		switch(timestamp % 3) {
		case 0: return 0;
		case 1:
		case 2: return 2;
		default: {
			timestamp = time(nullptr);
		}
		}
		timestamp *= 3;
		return timestamp % 2;
	}
};

int main() {
	ExampleClass obj1;
	return obj1.switchExample(3);
}
