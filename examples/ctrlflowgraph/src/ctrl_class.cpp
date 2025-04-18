///

#include <time.h>       // time


namespace item {
    class EmptyExamle {
    };

    class ExampleA;

    int funcA(ExampleA* object) {
        return 1;
    }

    class ExampleA {
    public:

        int fieldA;

        ExampleA(): fieldA(5) {
        }

        virtual ~ExampleA() {
        }

        virtual int methodA1() {
            int ret = 5;
            EmptyExamle emptyObj;
            ret += funcA(this);
            return ret;
        }
    };

    class ExampleB {
    public:
        ExampleA objA;

        int methodB1(const int param) {
            const float var1 = 3.3 * param;
            const float var2 = param * 3.3;
            const int valA = objA.methodA1();
            int retX = methodB2(var1) * valA;
            retX += 7;
            int retY = methodB3(12);
            return retX + retY;
        }

        static int methodB3(const int val) {
            return val;
        }


    private:

        int methodB2(const float param) {
            const float var = 6.6 * param;
            return static_cast<int>(var);
        }
    };

}
