///

namespace items1 {
	class VAbc1 {
	public:
		int field1;
	};


	class Abc2 {
	public:
		bool fieldA;
	};


	class Abc3: virtual public VAbc1, public Abc2 {
	public:
	};
}


namespace items2 {
	class Bbc1 {
	public:
		int field1;
	};


	class VBbc2 {
	public:
		bool fieldA;
	};


	class Bbc3: Bbc1, virtual public VBbc2 {
	public:
	};
}


namespace items3 {
	class Cbc1 {
	public:

		int fieldA;

		virtual int funcA() = 0;
	};


	class Cbc2: public Cbc1 {
	public:

		int fieldB;

		int funcA() override {
			return 12321;
		}

		virtual int funcB() = 0;
	};


	class Cbc3: public Cbc2 {
	public:

		int fieldC;

		int funcA() override {
			return 32123;
		}

		int funcB() override {
			return 54345;
		}
	};
}


namespace items4 {
	class Dbc1 {
	public:

		int fieldA;

		virtual int funcDA() = 0;
	};

	class Dbc2 {
	public:

		int fieldB;

		virtual int funcDB() = 0;
	};


	class Dbc3: public Dbc1, public Dbc2 {
	public:

		int fieldC;

		int funcDA() override {
			return 32123;
		}

		int funcDB() override {
			return 54345;
		}
	};
}


//int main() {
//	items3::Cbc1* obj = new items3::Cbc3();
//	const int ret_val = obj->funcA();
//	delete obj;
//	return ret_val;
//}
