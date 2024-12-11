///

namespace items {
	class Abc1 {
	public:
		int field;
	};


	class Abc2A: virtual public Abc1 {
	public:
	};


	class Abc2B: virtual public Abc1 {
	public:
	};
}


class Abc3: public items::Abc2A, public items::Abc2B {
public:
};
