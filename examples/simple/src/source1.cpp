///

namespace items {
	class Abc {
	public:
		int field1;
		double field2;

		Abc(int field_1, double field_2): field1(field_1), field2(field_2) {
		}

		int getval() const {
			return field1;
		}
		void callfunc1() {
		}
	};


	class Abc2 {
	public:
		void callfunc2() {
		}
	};


	class Abc3: public Abc, protected Abc2 {
	private:
		int fieldC = 0;

	public:
		Abc3(): Abc(2, 3.0) {
		}

		void callfunc3() {
		}
	};
}


int main() {
	items::Abc3 obj;
    obj.getval();
    return 0;
}
