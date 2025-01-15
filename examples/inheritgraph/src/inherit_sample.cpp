///

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
		char fieldD;
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


	class TemplInherit: public AbcTempl<int, bool> {
	public:
		int fieldA;
	};


	class TemplInheritDouble: public AbcTempl<int, int>, public AbcTempl<double, double> {
	public:
		bool dataA;
	};

}


namespace membersns {

	class BaseClass {
	public:
		bool publicFieldA;

	public:
		bool protectedFieldB;

	private:

		int privateFieldC;

	public:

		BaseClass() = default;

		virtual ~BaseClass() = default;

		int regularFn(int paramA, bool /*paramB*/) { return 0; }

		virtual int* virtFn() { return nullptr; }

		static void staticFn(const double paramA) {}

	protected:

		virtual void virtPureFn() = 0;

	};


	class SubClass final: public BaseClass {
	public:

		int* virtFn() override { return nullptr; }

	protected:
		static const int staticField;

		void virtPureFn() override final {};
	};

}
