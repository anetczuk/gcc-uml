///

namespace items {
	class Abc1 {
	public:
		int field1;
		double field2;

		void callfunc1() {
		}
	};


	class Abc2 {
	public:
		void callfunc2() {
		}
	};


	class Abc3 {
	public:
		void callfunc2() {
		}
	};
}


class Abc4A: virtual items::Abc1, public items::Abc2, protected items::Abc3 {
public:
	void callfunc4a() {
	}
};
