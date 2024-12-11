///

namespace items {
	class Abc1 {
	public:
	};


	class Abc2 {
	public:
	};
}


class Abc3: virtual public items::Abc1, public items::Abc2 {
public:
};
