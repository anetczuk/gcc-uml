///

namespace items {
	class Abc1 {
	public:
		int field1;
		double field2;

		void callfunc1() {
		}
	};


	class Abc2: private Abc1 {
	public:
		void callfunc2() {
		}
	};


	class Abc3: protected Abc2 {
	public:
		void callfunc3() {
		}
	};


	class Abc4: public Abc3 {
	public:
		void callfunc4() {
		}
	};


	/// default inheritance
	class Abc5: Abc4 {
	public:
		void callfunc5() {
		}
	};

}
