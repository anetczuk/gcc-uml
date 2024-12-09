///

namespace items {
	class Abc1 {
	public:

		Abc1() {}

		virtual void callfunc1() {
		}

		virtual void callfunc2() = 0;
	};


	class Abc2: public Abc1 {
	public:
		void callfunc2() override {
		}
	};


	class Abc3: public Abc2 {
	public:

		int field;

		void callfunc3() {
		}

		bool callfunc4() {
			return false;
		}

		bool callfunc5() const {
			return false;
		}

		int* callfunc6_ptr1() {
			return &field;
		}

		const int* callfunc6_ptr2() {
			return &field;
		}

		int& callfunc6_ref() {
			return field;
		}

		const int& callfunc6_ref2() {
			return field;
		}

	};
}
