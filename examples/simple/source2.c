///

int func_aaa(const int aaa) {
	const int bbb = aaa * 2;
    return bbb;
}


namespace xxx {
	int func_bbb1(int param) {
		const int bbb1 = param * 3;
		return bbb1;
	}
	int func_bbb2(int param) {
		const int bbb2 = param * 4;
		return bbb2;
	}
}
