///

namespace items {
    class Abc1 {
    public:
        static bool static1;
        static const int static2;

    protected:
        int field1;
        double field2;

    private:
        const double field3;
        long double field4;
        long int field5;
        long field6;
        long long field7;

    public:
        virtual ~Abc1() {
        }

        void call_param(int paramA, const double paramB, bool /*paramC*/) {
        }

        virtual void call_virt(int paramA = 0) {
        }

        virtual void call_pure(int paramA, const double paramB, bool /*paramC*/) = 0;

        static void call_static(int paramA, const double paramB, bool /*paramC*/) {
        }

    };
}
