/// type trait example

namespace items {

    struct DataBase {
        int field1;
    };

    using UsingData = DataBase;

    typedef DataBase TypedefData;


    struct Data2Base {

        using Using3Data = DataBase;

        typedef DataBase Typedef3Data;

        int field2;
    };

}
