///

namespace items {
	class Abc1A {
	public:
	};


	class Abc1B {
	public:
		Abc1B() = default;
	};


	class Abc1C {
	public:

		Abc1C() {};

	};


	class Abc2 {
	public:

		Abc2(const Abc2& /*item*/) {};

	};


	class Abc3A {
	public:

		~Abc3A() = default;

	};


	class Abc3B {
	public:

		virtual ~Abc3B() = default;

	};


	class Abc3C {
	public:

		~Abc3C() {};

	};


	class Abc3D {
	public:

		virtual ~Abc3D() {}

	};



//	class AbcRuleOfFive {
//	public:
//
//		AbcRuleOfFive(const Abc3B& /*item*/) {};
//
//	    base_of_five_defaults(const base_of_five_defaults&) = default;
//	    base_of_five_defaults(base_of_five_defaults&&) = default;
//	    base_of_five_defaults& operator=(const base_of_five_defaults&) = default;
//	    base_of_five_defaults& operator=(base_of_five_defaults&&) = default;
//	    virtual ~base_of_five_defaults() = default;
//
//	};
}
