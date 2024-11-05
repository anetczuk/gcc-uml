///

class Abc {
public:
    int field1;
    double field2;
    
    int getval() const {
        return field1;
    }
};


int main() {
    Abc obj;
    obj.getval();
    return 0;
}