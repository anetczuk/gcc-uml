///

class Base1 {
public:
	virtual int method1() = 0;
};

class Abc1 final: public Base1 {
public:
	int field1;
	int method1() final override {
		return field1;
	}
};
