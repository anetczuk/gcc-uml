/// example is taken from "gcc/testsuite/g++.dg/other/pr113617.h" of GCC project

namespace {

    template <int V>
    struct JJJ { static constexpr int jjjvalue = V; };

    template <bool V2>
    using KKK = JJJ<V2>;

    using MMM = KKK<true>;

    template <int>
    struct LLL {
        template <typename _Tp, typename>
        using llltype = _Tp;
    };

    template <bool _Cond, typename _If, typename _Else>
    using NNN = typename LLL<_Cond>::llltype<_If, _Else>;

    template <typename _Tp>
    struct OOO {
        using oootype = _Tp;
    };

    template <typename _Up>
    struct PPP : NNN<MMM ::jjjvalue, OOO<_Up>, _Up> {
    };

    template <typename _Tp>
    struct QQQ {
        using qqqtype = typename PPP<_Tp>::oootype;
    };
}
