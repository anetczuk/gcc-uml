///

namespace items {
    class Abc1 {
    public:

        void call1_param(int paramA, const double paramB, bool /*paramC*/) {
        }

        void call2_ptr(int* paramA, const int* paramB, int const* paramC, int* const paramD) {
        }

        void call2_ptr(int** paramA, const int** paramB, int const** paramC, int** const paramD) {
        }

        void call3_ref(int& paramA, const int& paramB, int const& paramC) {
        }

    };
}
