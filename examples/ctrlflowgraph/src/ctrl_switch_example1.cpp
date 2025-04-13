#include <cstdio>


int check_switch(const int value) {
    printf("value: %i\n", value);
    switch(value) {
    case 0: {
        printf("    case 0 (with fallthrough)\n");
    }
    case 1: {
        printf("    case 1\n");
        break;
    }
    case 2: {
        printf("    case 2\n");
        break;
    }
    default: {
        printf("    case default\n");
        break;
    }
    }
    return value;
}


int main() {
    check_switch(0);
    check_switch(1);
    check_switch(2);
    check_switch(3);
    return 0;
}
