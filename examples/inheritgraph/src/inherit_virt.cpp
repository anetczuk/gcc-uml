///

namespace items1 {
	class VAbc1 {
	public:
		int fieldA1;
	};


	class Abc2 {
	public:
		bool fieldB1;
	};


	class Abc3: virtual public VAbc1, protected Abc2 {
	public:
		char fieldC1;
	};
}


namespace items2 {
	class Bbc1 {
	public:
		int fieldA2;
	};


	class VBbc2 {
	public:
		bool fieldB2;
	};


	class Bbc3: protected Bbc1, virtual public VBbc2 {
	public:
		char fieldC2;
	};
}


namespace items3 {
	class Cbc1 {
	public:

		int fieldA3;

		virtual int funcA() = 0;
	};


	class Cbc2: public Cbc1 {
	public:

		int fieldB3;

		int funcA() override {
			return 12321;
		}

		virtual int funcB() = 0;
	};


	class Cbc3: public Cbc2 {
	public:

		int fieldC3;

		int funcA() override {
			return 32123;
		}

		int funcB() override {
			return 54345;
		}
	};
}
