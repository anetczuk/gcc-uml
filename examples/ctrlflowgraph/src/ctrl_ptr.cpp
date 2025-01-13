///

namespace item {
	class ExampleA {
	public:
		virtual void methodB1() {}
		virtual void methodB2() {}
	};

	class ExampleB: public ExampleA {
	public:
		void methodB1() override {}
		void methodB2() override {}
	};
}


void funcA() {
	item::ExampleB objB;
	item::ExampleA *ptrA = &objB;

	ptrA->methodB2();
	ptrA->methodB1();
}
