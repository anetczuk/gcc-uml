///

int func_a1(const int aaa) {
	const int bbb = aaa * 2;
    return bbb;
}


namespace xxx {
	int func_b1(int param) {
		const int bbb1 = param * 3;
		return bbb1;
	}
	int func_b2(int paramA, const int paramB) {
		const int bbb2 = paramA * paramB;
		return bbb2;
	}
	inline int func_b3(const int paramA, const int paramB) {
		const int bbb1 = func_b1(paramA) * paramB;
		const int bbb2 = bbb1 + 2;
		return bbb2;
	}
}
