///

namespace property {
    class Animal {
    public:
        double weight;
        double width;
        double height;
    };


    class FlyingAnimal: public Animal {
    public:
        double flydistance = 0.0;
        void fly(const double distance) {
            flydistance += distance;
        }
    };


    class WalkingAnimal: public Animal {
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
