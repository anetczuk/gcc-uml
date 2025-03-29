/// type trait example

namespace items {

    template <class TType>
    class Trait: public TType::DataType {
    };


    struct Data {
        using DataType = int;
    };


    struct BaseStruct {
        using DataType = Data;
    };


    inline void func() {
        Trait<BaseStruct> example;
    }

}
