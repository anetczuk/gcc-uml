/// unusual use of switch with some abuse

int calc_val(const int param) {
    int value = 0;
    int val2 = 0;
    switch(param) {
        value += 1;
    case 0:
        value += 10;
    case 1:
        if (value % 2 == 0 ) {
    case 2:
            value += 100;
        } else {
            value += 1000;
            break;
        }
        val2 += 1;
    default:
        val2 += 10;
    }
    return value;
}


int main() {
    return calc_val(0);
}
