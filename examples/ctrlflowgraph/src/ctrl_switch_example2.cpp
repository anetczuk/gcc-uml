#include <cstdio>


int check_switch(const int value) {
    printf("value: %i\n", value);

    switch(value) {
        case 0:
        printf("    case 0\n");
        if ( value % 2 == 0 ) {
            case 1:
            printf("    value is even\n");
        } else {
            case 2:
            printf("    value is odd\n");
        }
        break;

        default:
        printf("    case default\n");
        break;
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
