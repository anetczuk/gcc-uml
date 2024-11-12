///

namespace items {
	class Abc {
	public:
		int field1;
		double field2;

		Abc(int field1, double field2): field1(field1), field2(field2) {
		}

		int getval() const {
			return field1;
		}
	};


	class Abc2: public Abc {
	public:
		Abc2(): Abc(2, 3.0) {
		}

		void callfunc() {
		}
	};
}


int main() {
	items::Abc2 obj;
    obj.getval();
    return 0;
}
