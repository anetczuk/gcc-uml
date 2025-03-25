///

#include <time.h>       // time


int calc_val2() {
    int timestamp = time(nullptr);
    const int value = timestamp % 3;
    switch(value) {
    case 0:
        /// do nothing -- fallthrough
        [[fallthrough]];
    case 1: {
        timestamp = time(nullptr);
    }
    default: {
        return -1;
    }
    case 2: break;
    case 3: return 2;
    case 4: {
        int ret = timestamp + value;
        ret -= value;
        return ret;
    }
    case 5: {
        timestamp = time(nullptr);
    }
    }
    return -9;
}


int calc_val1() {
    int timestamp = time(nullptr);
    const int value = timestamp % 3;
    switch(value) {
    case 0: /// do nothing -- fallthrough
    case 1: {
        timestamp = time(nullptr);
    }
    case 2: break;
    case 3: return 2;
    case 4: {
        int ret = timestamp + value;
        ret /= value;
        ret /= 5.2;
        return ret;
    }
    case 5: {
        timestamp = time(nullptr);
    }
    default: return -1;
    }
    return -9;
}
