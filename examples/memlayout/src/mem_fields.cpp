///

namespace itemsA {

	namespace subA {
		struct Stu1 {
		public:

			int fieldA;
			bool fieldB;
			double fieldC;
			bool fieldD;
			float fieldE;

		};
	}


	struct Stu2 {
	public:

		int fieldA;
		bool fieldB;
		int fieldC;
		bool fieldD;
		bool fieldE;
		bool fieldF;

	};


	class Abc1 {
	public:

		int fieldA;
		bool fieldB;
		double fieldC;
		bool fieldD;
		float fieldE;

	};


	class Abc2 {
	public:

		bool dataA;
		subA::Stu1 dataB;
		bool dataC;
		subA::Stu1* dataD1;
		Stu2** dataD2;
		bool dataE;
		Abc1& dataF;
	};

}


namespace itemsB {

	class Abc3: public itemsA::Abc1, public itemsA::Stu2 {
	public:

		int dataA;
		Abc1 dataB;
		int dataC;
	};

}


namespace itemsC {

	class Abc4: public itemsB::Abc3 {
	public:

		virtual ~Abc4() = default;

		int dataA;
	};
}
