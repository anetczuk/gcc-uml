///

short foo(short p2) {
    return p2 + 1;
}

void compound001() {
    short aaa1 = 0;
    aaa1 = foo( (1, 2) );				/// compound_expr
    aaa1 = foo( (3, foo(4)) );			/// compound_expr
    aaa1 = foo( (foo(5), 6) );			/// compound_expr
    aaa1 = foo( (foo(7), foo(8)) );		/// compound_expr
}

void truth_if001() {
    int a = 0;
    int b = 0;
    int c = a && b;
}

int goto001() {
    int ggg1 = 0;
    if (ggg1) {
        goto err_not_found;
    }
    return 1;
err_not_found:
    return 2;
}

void increment001() {
    int www1 = 0;
    ++www1;
    --www1;
    www1++;
    www1--;
}

void compare001() {
    int www1 = 0;
    if (www1 <= 10) {
        www1++;
    }
    if (www1 >= 10) {
        www1++;
    }
}

int asm001() {
    int res;
    __asm__ ( "movl $5, %%eax;": "=a"(res));
    return res;
}

void staticcast() {
    int res = 0;
    bool val = static_cast<bool>(res);
}

void staticcast(int aaa) {
    int res = 0;
    bool val = static_cast<bool>(res);
}

namespace over {
    /// snippet for generating "overload" tree entry
    void func1(void);
    void func1(int);
    template<class T>
    T func_over(void) {
        return &func1;
    }
    void func3() {
        void (*fptr)() = func_over< void (*)() >();
        fptr();
    }
}

void try_func() {
    int asd = 0;
    try {
        asd = 1;
    } catch(const char *exc) {
        asd = 2;
    } catch(int) {
        asd = 3;
    } catch(...) {
        asd = 4;
    }
}

void while_func(int iter) {
    while(iter > 0) {
        iter -= 2;
    }
}

void shift_func(int iter) {
    int b = iter << 1;
    int c = iter >> 2;
}

void throw_example() {
    throw "xxx";
}
