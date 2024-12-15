///

namespace items {
	class Abc1 {
	public:
	};


	class Abc2 {
	public:
	};
}


class Abc3: items::Abc1, virtual public items::Abc2 {
public:
};
