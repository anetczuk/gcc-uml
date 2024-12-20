///

namespace items {

	class AbcEmpty {
	};


	template<typename TTypeA, typename TTypeB>
	class AbcTempl {
	public:
		TTypeA field1;
		bool field2;
		TTypeB field3;
	};


	class Abc2A {
	public:
		int fieldA;
		AbcTempl<float, char> fieldB;
	};


	class Abc2B: public AbcTempl<int, bool> {
	public:
		int fieldA;
	};


	class Abc2C: public AbcTempl<int, int>, public AbcTempl<double, double> {
	public:
		bool dataA;
	};

}
