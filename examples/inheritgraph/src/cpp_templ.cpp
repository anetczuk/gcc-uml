///

namespace items {

	template<typename TTypeA, typename TTypeB>
	class Abc1 {
	public:
		TTypeA fieldA;
		TTypeB fieldB;
	};


	class Abc2A: public Abc1<int, bool> {
	};


	class Abc2B: public Abc1<float, char> {
	};


	class Abc2C: public Abc1<int, int>, public Abc1<double, double> {
	};


	class Abc3 {
	public:
		template<typename TType>
		void calc_templ(const TType value) {
		}
	};


	template<typename TType>
	void func_templ(const TType value) {
	}

}
