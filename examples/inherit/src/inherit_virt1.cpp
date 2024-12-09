///

namespace items {
	class Abc1 {
	public:
	};


	class Abc2 {
	public:
	};


	class Abc3 {
	public:
	};
}


class Abc4: virtual items::Abc1, public items::Abc2, protected items::Abc3 {
public:
};
