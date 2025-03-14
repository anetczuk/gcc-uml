///

#include <cstdint>

namespace diamondns {
	class Abc1 {
	public:
		int fieldA;
	};


	class Bbc1: virtual public Abc1 {
	public:
		bool fieldB;
	};

	class Bbc2: virtual public Abc1 {
	public:
		char fieldC;
	};


	class Cbc1: public Bbc1, public Bbc2 {
	public:
		int fieldD1;
		int fieldD2: 5;
		uint8_t : 2;					/// unnamed bitfield
		mutable uint8_t fieldD3: 5;
	};
}


namespace templatens {

	template<typename TTypeA, typename TTypeB>
	class AbcTempl {
	public:
		TTypeA field1;
		bool field2;
		TTypeB field3;
	};


	class TemplField {
	public:
		int fieldA;
		AbcTempl<float, char> fieldB;
	};


	class TemplInherit: public AbcTempl<int, bool> {
	public:
		int fieldA;
	};


	class TemplInheritDouble: public AbcTempl<int, int>, public AbcTempl<double, double> {
	public:
		bool dataA;
	};

}
