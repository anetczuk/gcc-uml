///

namespace property {
	class Animal {
	public:
		int size;
	};


	class FlyingAnimal: virtual public Animal {
	public:
		double flydistance = 0.0;
		void fly(const double distance) {
			flydistance += distance;
		}
	};


	class WalkingAnimal: virtual public Animal {
	public:
		double walkdistance = 0.0;
		void walk(const double distance) {
			walkdistance += distance;
		}
	};
}


class Duck: public property::FlyingAnimal, public property::WalkingAnimal {
public:
	int noquacks = 0;
	void quack() {
		++noquacks;
	}
};
