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
}


class Abc4B: items::Abc1, virtual public items::Abc2 {
public:
	void callfunc4b() {
	}
};
