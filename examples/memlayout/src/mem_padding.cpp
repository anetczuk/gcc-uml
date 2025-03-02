/// presentation of padding feature of C/++ language

#include <cstdint>


namespace padding {
    struct OptimalA {
        bool fieldA;
        uint8_t fieldB;
        uint16_t fieldC;
        uint32_t fieldD;
        uint64_t fieldE;
    };

    struct OptimalB {
        uint64_t fieldE;
        uint32_t fieldD;
        uint16_t fieldC;
        uint8_t fieldB;
        bool fieldA;
    };

    struct Suboptimal {
        bool fieldA;
        uint32_t fieldD;
        uint16_t fieldC;
        uint64_t fieldE;
        uint8_t fieldB;
    };

}


namespace pragmapack {

#pragma pack(push, 1)

    struct SuboptimalPack1 {
        bool fieldA;
        uint32_t fieldD;
        uint16_t fieldC;
        uint64_t fieldE;
        uint8_t fieldB;
    };

#pragma pack(pop)
#pragma pack(push, 2)

    struct SuboptimalPack2 {
        bool fieldA;
        uint32_t fieldD;
        uint16_t fieldC;
        uint64_t fieldE;
        uint8_t fieldB;
    };

#pragma pack(pop)

}
