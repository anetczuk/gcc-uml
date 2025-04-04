///


int calcA(const int paramA) {
    return paramA;
}


int calcB(const int valueI) {
    int valueB = 9;

    valueI == -22 ? calcA(1) : calcA(2);

    valueB += valueI == -11 ? 5 : 6;

    if (valueI == 1 ) {
        valueB *= 11;
    }

    if (valueI == 2 )
        valueB += 21;
    else
        valueB += 22;

    if (valueI == 3 ) {
        valueB += 31;
    } else {
        valueB *= 32;
    }

    return valueB;
}
