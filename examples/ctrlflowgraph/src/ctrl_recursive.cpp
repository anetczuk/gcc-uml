/// file taken from GCC compiler source code
/// gcc/testsuite/gcc.dg/tree-ssa/pr95867.c

#define A n * n * n * n * n * n * n * n
#define B A * A * A * A * A * A * A * A
#define C B * B * B * B * B * B * B * B

unsigned
foo (unsigned n)
{
  return C * B * B * A * n * n * n * n * n;
}
