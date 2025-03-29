/// example of Curiously recurring template pattern

namespace items {

    template <typename TBase>
    struct Wrapper: public TBase {
        TBase data;
    };


    struct BaseStruct {
    };


    inline void func() {
        Wrapper<BaseStruct> example;
    }
}
