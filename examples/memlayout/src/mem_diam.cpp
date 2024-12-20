///


namespace items {
	class Abc1 {
	public:
		int field;
	};


	class Abc2A: public Abc1 {
	public:
		bool fieldA;
	};


	class Abc2B: public Abc1 {
	public:
		bool fieldB;
	};


	class Abc3: public Abc2A, public Abc2B {
	public:
		int data;
	};
}


namespace virt1 {
	class Abc1 {
	public:
		int field;
	};


	class VAbc2A: virtual public Abc1 {
	public:
		bool fieldA;
	};


	class VAbc2B: virtual public Abc1 {
	public:
		bool fieldB;
	};


	class Abc3: public VAbc2A, public VAbc2B {
	public:
		int data;
	};
}


namespace virt2 {
	class Abc1 {
	public:
		int field;
	};


	class Abc2A: public Abc1 {
	public:
		bool fieldA;
	};


	class Abc2B: public Abc1 {
	public:
		bool fieldB;
	};


	class VAbc3: virtual public Abc2A, virtual public Abc2B {
	public:
		int data;
	};
}
