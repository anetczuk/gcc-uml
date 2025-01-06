///

#include <time.h>       // time


namespace item {
	class ExampleA {
	public:
		int methodA1() {
			return 5;
		}
	};

	class ExampleB {
	public:
		virtual int methodB1() {
			return 6;
		}
		virtual int methodB2() {
			return 7;
		}
	};

	class ExampleC: public ExampleB {
	public:
		int methodB1() override {
			return 16;
		}
		int methodB2() override {
			return 17;
		}
	};
}

int funcA() {
	int retX = 0;

//	item::ExampleA objA;
//	item::ExampleA *ptrA = &objA;
//	ret = ret + ptrA->methodA1();

	item::ExampleC objC;
	item::ExampleB *ptrB = &objC;
	retX = retX + ptrB->methodB2();

	return retX;
}
