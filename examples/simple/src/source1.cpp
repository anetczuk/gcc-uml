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
	};


	class Abc2 {
	};


	class Abc3: public Abc, private Abc2 {
	public:
		Abc3(): Abc(2, 3.0) {
		}

		void callfunc() {
		}
	};
}


int main() {
	items::Abc3 obj;
    obj.getval();
    return 0;
}
